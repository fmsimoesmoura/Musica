"""TidalApiGateway — the single adapter over the (unofficial) tidalapi library.

Implements both AuthGateway and MusicGateway. This is the *only* module that
imports tidalapi, so swapping to a different backend (e.g. Tidal's official API)
means rewriting just this file.
"""
from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import Future
from datetime import datetime
from typing import Any, Callable, Optional

import tidalapi

from ...domain.auth.entities import (
    ConnectionStatus,
    LinkLogin,
    LoginResult,
    LoginStatus,
    OAuthTokens,
)
from ...domain.catalog.entities import CatalogSearchResults
from ...domain.library.entities import Album, Artist, LibrarySnapshot, Playlist, Track

log = logging.getLogger("infra.tidal")

_PAGE = 100


class TidalApiGateway:
    def __init__(self) -> None:
        self._session = tidalapi.Session()
        self._lock = threading.Lock()
        self._pending: dict[str, Future] = {}

    # ---- AuthGateway --------------------------------------------------------
    def start_login(self) -> LinkLogin:
        login, future = self._session.login_oauth()
        login_id = uuid.uuid4().hex
        self._pending[login_id] = future
        uri = login.verification_uri_complete
        if uri and not uri.startswith("http"):
            uri = f"https://{uri}"
        return LinkLogin(
            login_id=login_id,
            verification_uri=uri,
            user_code=login.user_code,
            expires_in=int(getattr(login, "expires_in", 300)),
        )

    def poll_login(self, login_id: str) -> LoginResult:
        future = self._pending.get(login_id)
        if future is None:
            return LoginResult(status=LoginStatus.UNKNOWN)
        if not future.done():
            return LoginResult(status=LoginStatus.PENDING)

        self._pending.pop(login_id, None)
        if future.exception() is not None:
            log.warning("OAuth login failed/expired: %s", future.exception())
            return LoginResult(status=LoginStatus.EXPIRED)
        if self._is_connected():
            return LoginResult(
                status=LoginStatus.AUTHORIZED, connected=True, user_name=self._user_name()
            )
        return LoginResult(status=LoginStatus.EXPIRED)

    def status(self) -> ConnectionStatus:
        return ConnectionStatus(connected=self._is_connected(), user_name=self._user_name())

    def restore(self, tokens: OAuthTokens) -> bool:
        try:
            self._session.load_oauth_session(
                token_type=tokens.token_type,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                expiry_time=tokens.expiry_time,
            )
        except Exception as e:
            log.warning("Failed to load stored session: %s", e)
            return False
        if self._is_connected():
            return True
        if tokens.refresh_token:
            try:
                if self._session.token_refresh(tokens.refresh_token) and self._is_connected():
                    return True
            except Exception as e:
                log.warning("Token refresh failed: %s", e)
        return False

    def current_tokens(self) -> Optional[OAuthTokens]:
        s = self._session
        if not s.access_token:
            return None
        expiry = s.expiry_time
        return OAuthTokens(
            token_type=s.token_type,
            access_token=s.access_token,
            refresh_token=s.refresh_token,
            expiry_time=expiry if isinstance(expiry, datetime) else None,
        )

    def disconnect(self) -> None:
        with self._lock:
            self._session = tidalapi.Session()

    # ---- MusicGateway -------------------------------------------------------
    def fetch_library_snapshot(self) -> LibrarySnapshot:
        user = self._session.user
        snap = LibrarySnapshot()
        seen_artists: dict[str, Artist] = {}
        seen_albums: dict[str, Album] = {}
        seen_tracks: dict[str, Track] = {}

        def remember_track(t: Any) -> int:
            tid = str(t.id)
            artist = _attr(t, "artist")
            album = _attr(t, "album")
            if artist and str(artist.id) not in seen_artists:
                seen_artists[str(artist.id)] = _artist(artist)
            if album and str(album.id) not in seen_albums:
                seen_albums[str(album.id)] = _album(album)
            seen_tracks[tid] = _track(t)
            return tid

        for pl in list(user.playlists()):
            snap.playlists.append(_playlist(pl))
            track_ids = [remember_track(t) for t in _paginate(lambda l, o, _p=pl: _p.tracks(l, o))]
            snap.playlist_tracks[str(pl.id)] = track_ids

        fav = user.favorites
        snap.favorite_track_ids = [remember_track(t) for t in _paginate(lambda l, o: fav.tracks(l, o))]
        for a in _paginate(lambda l, o: fav.artists(l, o)):
            seen_artists.setdefault(str(a.id), _artist(a))
            snap.favorite_artist_ids.append(str(a.id))
        for al in _paginate(lambda l, o: fav.albums(l, o)):
            seen_albums.setdefault(str(al.id), _album(al))
            snap.favorite_album_ids.append(str(al.id))

        snap.artists = list(seen_artists.values())
        snap.albums = list(seen_albums.values())
        snap.tracks = list(seen_tracks.values())
        return snap

    # ---- CatalogGateway -----------------------------------------------------
    def search(self, query: str, include: list[str]) -> CatalogSearchResults:
        model_map = {
            "artists": tidalapi.Artist,
            "albums": tidalapi.Album,
            "tracks": tidalapi.Track,
        }
        models = [model_map[i] for i in include if i in model_map]
        raw = self._session.search(query, models=models or None, limit=30)
        results = CatalogSearchResults()
        if "artists" in include:
            results.artists = [_artist(a) for a in (raw.get("artists") or [])]
        if "albums" in include:
            results.albums = [_album(a) for a in (raw.get("albums") or [])]
        if "tracks" in include:
            results.tracks = [_track(t) for t in (raw.get("tracks") or [])]
        return results

    # ---- FavoritesGateway ---------------------------------------------------
    def add(self, item_type: str, item_id: str) -> bool:
        fav = self._session.user.favorites
        fn = {"track": fav.add_track, "artist": fav.add_artist, "album": fav.add_album}[item_type]
        return bool(fn(item_id))

    def remove(self, item_type: str, item_id: str) -> bool:
        fav = self._session.user.favorites
        fn = {
            "track": fav.remove_track,
            "artist": fav.remove_artist,
            "album": fav.remove_album,
        }[item_type]
        return bool(fn(item_id))

    # ---- RecommendationGateway ----------------------------------------------
    def similar_artists(self, artist_id: str) -> list[Artist]:
        artist = self._session.artist(artist_id)
        try:
            return [_artist(a) for a in (artist.get_similar() or [])]
        except Exception as e:
            log.warning("get_similar failed for artist %s: %s", artist_id, e)
            return []

    def artist_top_tracks(self, artist_id: str, limit: int = 1) -> list[str]:
        try:
            tracks = self._session.artist(artist_id).get_top_tracks(limit=limit)
            return [str(t.id) for t in (tracks or [])]
        except Exception as e:
            log.warning("get_top_tracks failed for artist %s: %s", artist_id, e)
            return []

    # ---- PlaylistWriter ------------------------------------------------------
    def create_playlist(self, title: str, description: str = "") -> str:
        pl = self._session.user.create_playlist(title, description or "")
        return str(pl.id)

    def add_tracks(self, playlist_id: str, track_ids: list[str]) -> None:
        self._writable(playlist_id).add([str(t) for t in track_ids])

    def remove_track(self, playlist_id: str, track_id: str) -> None:
        self._writable(playlist_id).remove_by_id(str(track_id))

    def edit_playlist(self, playlist_id: str, title: str | None, description: str | None) -> None:
        self._writable(playlist_id).edit(title=title, description=description)

    def delete_playlist(self, playlist_id: str) -> None:
        self._writable(playlist_id).delete()

    def fetch_playlist(self, playlist_id: str) -> LibrarySnapshot:
        """Re-read a single playlist (+its tracks) into a snapshot for local refresh."""
        pl = self._session.playlist(playlist_id)
        snap = LibrarySnapshot()
        seen_artists: dict[str, Artist] = {}
        seen_albums: dict[str, Album] = {}
        seen_tracks: dict[str, Track] = {}
        snap.playlists.append(_playlist(pl))
        ids: list[str] = []
        for t in _paginate(lambda l, o, _p=pl: _p.tracks(l, o)):
            artist = _attr(t, "artist")
            album = _attr(t, "album")
            if artist and str(artist.id) not in seen_artists:
                seen_artists[str(artist.id)] = _artist(artist)
            if album and str(album.id) not in seen_albums:
                seen_albums[str(album.id)] = _album(album)
            seen_tracks[str(t.id)] = _track(t)
            ids.append(str(t.id))
        snap.playlist_tracks[str(pl.id)] = ids
        snap.artists = list(seen_artists.values())
        snap.albums = list(seen_albums.values())
        snap.tracks = list(seen_tracks.values())
        return snap

    def _writable(self, playlist_id: str) -> "tidalapi.playlist.UserPlaylist":
        return tidalapi.playlist.UserPlaylist(self._session, playlist_id)

    # ---- internals ----------------------------------------------------------
    def _is_connected(self) -> bool:
        try:
            return bool(self._session.check_login())
        except Exception:
            return False

    def _user_name(self) -> Optional[str]:
        if not self._is_connected():
            return None
        try:
            u = self._session.user
            return getattr(u, "first_name", None) or getattr(u, "username", None) or str(u.id)
        except Exception:
            return None


# ---- extraction helpers (tidalapi object -> domain entity) ------------------

def _attr(obj: Any, *names: str, default=None):
    for n in names:
        v = getattr(obj, n, None)
        if v is not None:
            return v
    return default


def _paginate(fetch: Callable[[int, int], list]) -> list:
    out: list = []
    offset = 0
    while True:
        page = fetch(_PAGE, offset)
        if not page:
            break
        out.extend(page)
        if len(page) < _PAGE:
            break
        offset += _PAGE
    return out


def _img_url(uuid: Any, size: int = 320) -> Optional[str]:
    """Tidal image UUIDs map to URLs by replacing dashes with path separators."""
    if not uuid or not isinstance(uuid, str):
        return None
    return f"https://resources.tidal.com/images/{uuid.replace('-', '/')}/{size}x{size}.jpg"


def _artist(a: Any) -> Artist:
    return Artist(id=str(a.id), name=_attr(a, "name", default=""), picture=_img_url(_attr(a, "picture")))


def _album(al: Any) -> Album:
    artist = _attr(al, "artist")
    return Album(
        id=str(al.id),
        title=_attr(al, "name", "title", default=""),
        artist_id=str(artist.id) if artist else None,
        artist_name=_attr(artist, "name") if artist else None,
        cover=_img_url(_attr(al, "cover")),
        num_tracks=_attr(al, "num_tracks"),
        release_date=str(_attr(al, "release_date", default="")) or None,
    )


def _track(t: Any) -> Track:
    artist = _attr(t, "artist")
    album = _attr(t, "album")
    return Track(
        id=str(t.id),
        title=_attr(t, "name", "title", default=""),
        duration=_attr(t, "duration"),
        artist_id=str(artist.id) if artist else None,
        artist_name=_attr(artist, "name") if artist else None,
        album_id=str(album.id) if album else None,
        album_title=_attr(album, "name", "title") if album else None,
        isrc=_attr(t, "isrc"),
        image=_img_url(_attr(album, "cover")) if album else None,
        explicit=_attr(t, "explicit"),
    )


def _playlist(pl: Any) -> Playlist:
    creator = _attr(pl, "creator")
    return Playlist(
        id=str(pl.id),
        title=_attr(pl, "name", "title", default=""),
        description=_attr(pl, "description"),
        num_tracks=int(_attr(pl, "num_tracks", default=0) or 0),
        creator=_attr(creator, "name") if creator else None,
        picture=_img_url(_attr(pl, "picture", "square_picture")),
        last_updated=str(_attr(pl, "last_updated", default="")) or None,
    )
