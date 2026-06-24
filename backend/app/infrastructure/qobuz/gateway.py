"""QobuzGateway — adapter over the (unofficial) Qobuz v0.2 REST API.

Auth is email/password (not OAuth): login returns a long-lived user_auth_token,
sent on every request as X-User-Auth-Token alongside X-App-Id. Implements
AuthGateway (credentials login), MusicGateway, CatalogGateway, FavoritesGateway,
PlaylistWriter. Discovery similar-artists comes from Last.fm (see composition).
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

import requests

from ...config import qobuz_app_id
from ...domain.auth.entities import ConnectionStatus, LinkLogin, LoginResult, LoginStatus, OAuthTokens
from ...domain.catalog.entities import CatalogSearchResults
from ...domain.library.entities import Album, Artist, LibrarySnapshot, Playlist, Track

log = logging.getLogger("infra.qobuz")

API = "https://www.qobuz.com/api.json/0.2"
_PAGE = 100


class QobuzGateway:
    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._user_name: Optional[str] = None

    # ---- AuthGateway --------------------------------------------------------
    # Qobuz has no browser flow; the UI uses the credentials path below instead.
    def start_login(self) -> LinkLogin:
        raise RuntimeError("Qobuz uses email/password — connect with your credentials.")

    def poll_login(self, login_id: str) -> LoginResult:
        return LoginResult(status=LoginStatus.UNKNOWN)

    def login_with_credentials(self, username: str, password: str) -> bool:
        if not qobuz_app_id():
            raise RuntimeError(
                "QOBUZ_APP_ID is not set. Add it in Settings (scraped from the Qobuz web player)."
            )
        md5 = hashlib.md5(password.encode()).hexdigest()
        param = "email" if "@" in username else "username"
        data = self._get("user/login", {param: username, "password": md5}, auth=False)
        token = data.get("user_auth_token")
        if not token:
            return False
        self._token = token
        user = data.get("user") or {}
        self._user_name = user.get("display_name") or user.get("login") or user.get("email")
        return True

    def status(self) -> ConnectionStatus:
        if not self._token:
            return ConnectionStatus(connected=False, user_name=None)
        try:
            self._get("favorite/getUserFavorites", {"type": "tracks", "limit": 1})
        except Exception:
            return ConnectionStatus(connected=False, user_name=None)
        return ConnectionStatus(connected=True, user_name=self._user_name or "Qobuz account")

    def restore(self, tokens: OAuthTokens) -> bool:
        self._token = tokens.access_token
        return self.status().connected

    def current_tokens(self) -> Optional[OAuthTokens]:
        if not self._token:
            return None
        return OAuthTokens(token_type="qobuz", access_token=self._token, refresh_token=None, expiry_time=None)

    def disconnect(self) -> None:
        self._token = self._user_name = None

    # ---- CatalogGateway -----------------------------------------------------
    def search(self, query: str, include: list[str]) -> CatalogSearchResults:
        data = self._get("catalog/search", {"query": query, "limit": 30})
        res = CatalogSearchResults()
        if "artists" in include:
            res.artists = [_artist(a) for a in _items(data, "artists")]
        if "albums" in include:
            res.albums = [_album(a) for a in _items(data, "albums")]
        if "tracks" in include:
            res.tracks = [_track(t) for t in _items(data, "tracks")]
        return res

    # ---- FavoritesGateway ---------------------------------------------------
    def add(self, item_type: str, item_id: str) -> bool:
        self._get("favorite/create", {f"{item_type}_ids": item_id})
        return True

    def remove(self, item_type: str, item_id: str) -> bool:
        self._get("favorite/delete", {f"{item_type}_ids": item_id})
        return True

    # ---- PlaylistWriter -----------------------------------------------------
    def create_playlist(self, title: str, description: str = "") -> str:
        data = self._get("playlist/create", {"name": title, "description": description or "", "is_public": "false"})
        return str(data.get("id"))

    def add_tracks(self, playlist_id: str, track_ids: list[str]) -> None:
        self._get("playlist/addTracks", {"playlist_id": playlist_id, "track_ids": ",".join(track_ids)})

    def remove_track(self, playlist_id: str, track_id: str) -> None:
        # Qobuz removes by playlist_track_id, not track id — resolve it first.
        data = self._get("playlist/get", {"playlist_id": playlist_id, "extra": "tracks", "limit": 1000})
        for item in _items(data, "tracks"):
            if str(item.get("id")) == str(track_id):
                ptid = item.get("playlist_track_id") or item.get("id")
                self._get("playlist/deleteTracks", {"playlist_id": playlist_id, "playlist_track_ids": str(ptid)})
                return

    def edit_playlist(self, playlist_id: str, title: str | None, description: str | None) -> None:
        params: dict[str, Any] = {"playlist_id": playlist_id}
        if title is not None:
            params["name"] = title
        if description is not None:
            params["description"] = description
        if len(params) > 1:
            self._get("playlist/update", params)

    def delete_playlist(self, playlist_id: str) -> None:
        self._get("playlist/delete", {"playlist_id": playlist_id})

    def artist_top_tracks(self, artist_id: str, limit: int = 1) -> list[str]:
        name = self.get_artist_name(artist_id)
        if not name:
            return []
        data = self._get("catalog/search", {"query": name, "limit": limit, "type": "tracks"})
        return [str(t["id"]) for t in _items(data, "tracks")[:limit]]

    def get_artist_name(self, artist_id: str) -> Optional[str]:
        try:
            return self._get("artist/get", {"artist_id": artist_id, "limit": 0}).get("name")
        except Exception:
            return None

    # ---- MusicGateway -------------------------------------------------------
    def fetch_library_snapshot(self) -> LibrarySnapshot:
        snap = LibrarySnapshot()
        artists: dict[str, Artist] = {}
        albums: dict[str, Album] = {}
        tracks: dict[str, Track] = {}

        def remember(t: dict) -> Optional[str]:
            if not t or t.get("id") is None:
                return None
            tid = str(t["id"])
            perf = t.get("performer") or t.get("artist") or {}
            if perf.get("id") is not None:
                artists.setdefault(str(perf["id"]), _artist(perf))
            al = t.get("album") or {}
            if al.get("id") is not None:
                albums.setdefault(str(al["id"]), _album(al))
            tracks[tid] = _track(t)
            return tid

        for pl in self._paginate("playlist/getUserPlaylists", {}, "playlists"):
            snap.playlists.append(_playlist(pl))
            ids: list[str] = []
            for t in self._paginate("playlist/get", {"playlist_id": pl["id"], "extra": "tracks"}, "tracks"):
                tid = remember(t)
                if tid:
                    ids.append(tid)
            snap.playlist_tracks[str(pl["id"])] = ids

        for t in self._paginate("favorite/getUserFavorites", {"type": "tracks"}, "tracks"):
            tid = remember(t)
            if tid:
                snap.favorite_track_ids.append(tid)
        for a in self._paginate("favorite/getUserFavorites", {"type": "albums"}, "albums"):
            if a.get("id") is not None:
                albums.setdefault(str(a["id"]), _album(a))
                snap.favorite_album_ids.append(str(a["id"]))
        for a in self._paginate("favorite/getUserFavorites", {"type": "artists"}, "artists"):
            if a.get("id") is not None:
                artists.setdefault(str(a["id"]), _artist(a))
                snap.favorite_artist_ids.append(str(a["id"]))

        snap.artists = list(artists.values())
        snap.albums = list(albums.values())
        snap.tracks = list(tracks.values())
        return snap

    def fetch_playlist(self, playlist_id: str) -> LibrarySnapshot:
        snap = LibrarySnapshot()
        artists: dict[str, Artist] = {}
        albums: dict[str, Album] = {}
        tracks: dict[str, Track] = {}
        meta = self._get("playlist/get", {"playlist_id": playlist_id, "extra": "tracks", "limit": 1})
        snap.playlists.append(_playlist(meta))
        ids: list[str] = []
        for t in self._paginate("playlist/get", {"playlist_id": playlist_id, "extra": "tracks"}, "tracks"):
            if t.get("id") is None:
                continue
            perf = t.get("performer") or t.get("artist") or {}
            if perf.get("id") is not None:
                artists.setdefault(str(perf["id"]), _artist(perf))
            al = t.get("album") or {}
            if al.get("id") is not None:
                albums.setdefault(str(al["id"]), _album(al))
            tid = str(t["id"])
            tracks[tid] = _track(t)
            ids.append(tid)
        snap.playlist_tracks[str(playlist_id)] = ids
        snap.artists = list(artists.values())
        snap.albums = list(albums.values())
        snap.tracks = list(tracks.values())
        return snap

    # ---- internals ----------------------------------------------------------
    def _headers(self, auth: bool) -> dict:
        app_id = qobuz_app_id()
        if not app_id:
            raise RuntimeError("QOBUZ_APP_ID is not set.")
        h = {"X-App-Id": app_id}
        if auth and self._token:
            h["X-User-Auth-Token"] = self._token
        return h

    def _get(self, endpoint: str, params: dict, auth: bool = True) -> dict:
        resp = requests.get(f"{API}/{endpoint}", params=params, headers=self._headers(auth), timeout=30)
        if not resp.ok:
            raise RuntimeError(f"Qobuz {endpoint} -> {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def _paginate(self, endpoint: str, params: dict, key: str) -> list[dict]:
        out: list[dict] = []
        offset = 0
        while True:
            data = self._get(endpoint, {**params, "limit": _PAGE, "offset": offset})
            block = data.get(key, {})
            items = block.get("items", []) if isinstance(block, dict) else []
            if not items:
                break
            out.extend(items)
            total = block.get("total") if isinstance(block, dict) else None
            offset += _PAGE
            if total is not None and offset >= total:
                break
            if len(items) < _PAGE:
                break
        return out


# ---- helpers + mapping ----

def _items(data: dict, key: str) -> list[dict]:
    block = data.get(key, {})
    return block.get("items", []) if isinstance(block, dict) else []


def _img(image: Any) -> Optional[str]:
    if isinstance(image, dict):
        return image.get("large") or image.get("small") or image.get("thumbnail")
    return image if isinstance(image, str) else None


def _artist(a: dict) -> Artist:
    return Artist(id=str(a.get("id")), name=a.get("name", ""), picture=_img(a.get("image")))


def _album(al: dict) -> Album:
    artist = al.get("artist") or {}
    return Album(
        id=str(al.get("id")),
        title=al.get("title", ""),
        artist_id=str(artist["id"]) if artist.get("id") is not None else None,
        artist_name=artist.get("name"),
        cover=_img(al.get("image")),
        num_tracks=al.get("tracks_count"),
        release_date=al.get("release_date_original") or al.get("released_at"),
    )


def _track(t: dict) -> Track:
    perf = t.get("performer") or t.get("artist") or {}
    al = t.get("album") or {}
    return Track(
        id=str(t.get("id")),
        title=t.get("title", ""),
        duration=t.get("duration"),
        artist_id=str(perf["id"]) if perf.get("id") is not None else None,
        artist_name=perf.get("name"),
        album_id=str(al["id"]) if al.get("id") is not None else None,
        album_title=al.get("title"),
        isrc=t.get("isrc"),
        image=_img(al.get("image")),
        explicit=bool(t.get("parental_warning")),
    )


def _playlist(pl: dict) -> Playlist:
    owner = pl.get("owner") or {}
    return Playlist(
        id=str(pl.get("id")),
        title=pl.get("name", ""),
        description=pl.get("description"),
        num_tracks=pl.get("tracks_count", 0) or 0,
        creator=owner.get("name"),
        picture=None,
        last_updated=None,
    )
