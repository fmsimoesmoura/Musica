"""SpotifyGateway — the official Spotify Web API adapter.

Implements AuthGateway (Authorization Code + PKCE, loopback redirect),
MusicGateway, CatalogGateway, FavoritesGateway, and PlaylistWriter. The only file
that talks to Spotify. Discovery's similar-artists comes from Last.fm instead
(Spotify deprecated that endpoint), but artist top-tracks live here.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from ...config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPES,
)
from ...domain.auth.entities import (
    ConnectionStatus,
    LinkLogin,
    LoginResult,
    LoginStatus,
    OAuthTokens,
)
from ...domain.catalog.entities import CatalogSearchResults
from ...domain.library.entities import Album, Artist, LibrarySnapshot, Playlist, Track

log = logging.getLogger("infra.spotify")

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API = "https://api.spotify.com/v1"


class SpotifyGateway:
    def __init__(self) -> None:
        self._access: Optional[str] = None
        self._refresh: Optional[str] = None
        self._expiry: Optional[datetime] = None
        self._user_id: Optional[str] = None
        self._user_name: Optional[str] = None
        # In-flight logins keyed by OAuth `state` (which we also use as login_id).
        self._pending: dict[str, dict] = {}

    # ---- AuthGateway --------------------------------------------------------
    def start_login(self) -> LinkLogin:
        if not SPOTIFY_CLIENT_ID:
            raise RuntimeError(
                "SPOTIFY_CLIENT_ID is not set. Register a Spotify app and add it to backend/.env."
            )
        verifier = secrets.token_urlsafe(64)[:128]
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        state = secrets.token_urlsafe(16)
        self._pending[state] = {"verifier": verifier, "done": False, "error": None}
        url = AUTH_URL + "?" + urlencode(
            {
                "client_id": SPOTIFY_CLIENT_ID,
                "response_type": "code",
                "redirect_uri": SPOTIFY_REDIRECT_URI,
                "scope": SPOTIFY_SCOPES,
                "code_challenge_method": "S256",
                "code_challenge": challenge,
                "state": state,
            }
        )
        return LinkLogin(login_id=state, verification_uri=url, user_code="approve in browser", expires_in=600)

    def handle_callback(self, code: str | None, state: str | None, error: str | None) -> bool:
        pending = self._pending.get(state or "")
        if pending is None:
            return False
        if error or not code:
            pending["error"] = error or "no code"
            pending["done"] = True
            return False
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": SPOTIFY_REDIRECT_URI,
                    "client_id": SPOTIFY_CLIENT_ID,
                    "code_verifier": pending["verifier"],
                },
                timeout=15,
            )
            resp.raise_for_status()
            self._apply_token(resp.json())
            pending["done"] = True
            return True
        except requests.RequestException as e:
            log.warning("Spotify token exchange failed: %s", e)
            pending["error"] = str(e)
            pending["done"] = True
            return False

    def poll_login(self, login_id: str) -> LoginResult:
        pending = self._pending.get(login_id)
        if pending is None:
            return LoginResult(status=LoginStatus.UNKNOWN)
        if not pending["done"]:
            return LoginResult(status=LoginStatus.PENDING)
        self._pending.pop(login_id, None)
        if pending["error"]:
            return LoginResult(status=LoginStatus.EXPIRED)
        return LoginResult(status=LoginStatus.AUTHORIZED, connected=True, user_name=self._fetch_me())

    def status(self) -> ConnectionStatus:
        if not self._access:
            return ConnectionStatus(connected=False, user_name=None)
        name = self._fetch_me()
        return ConnectionStatus(connected=name is not None, user_name=name)

    def restore(self, tokens: OAuthTokens) -> bool:
        self._access = tokens.access_token
        self._refresh = tokens.refresh_token
        self._expiry = tokens.expiry_time
        try:
            self._ensure_token()
        except Exception as e:
            log.warning("Spotify restore/refresh failed: %s", e)
            return False
        return self._fetch_me() is not None

    def current_tokens(self) -> Optional[OAuthTokens]:
        if not self._access:
            return None
        return OAuthTokens(
            token_type="Bearer",
            access_token=self._access,
            refresh_token=self._refresh,
            expiry_time=self._expiry,
        )

    def disconnect(self) -> None:
        self._access = self._refresh = self._expiry = self._user_id = self._user_name = None

    # ---- CatalogGateway -----------------------------------------------------
    def search(self, query: str, include: list[str]) -> CatalogSearchResults:
        type_map = {"artists": "artist", "albums": "album", "tracks": "track"}
        types = ",".join(type_map[i] for i in include if i in type_map)
        data = self._get("/search", {"q": query, "type": types, "limit": 30})
        res = CatalogSearchResults()
        if "artists" in include:
            res.artists = [_artist(a) for a in data.get("artists", {}).get("items", [])]
        if "albums" in include:
            res.albums = [_album(a) for a in data.get("albums", {}).get("items", [])]
        if "tracks" in include:
            res.tracks = [_track(t) for t in data.get("tracks", {}).get("items", [])]
        return res

    # ---- FavoritesGateway ---------------------------------------------------
    def add(self, item_type: str, item_id: str) -> bool:
        if item_type == "artist":
            self._put("/me/following", params={"type": "artist", "ids": item_id})
        else:
            self._put(f"/me/{item_type}s", params={"ids": item_id})
        return True

    def remove(self, item_type: str, item_id: str) -> bool:
        if item_type == "artist":
            self._delete("/me/following", params={"type": "artist", "ids": item_id})
        else:
            self._delete(f"/me/{item_type}s", params={"ids": item_id})
        return True

    # ---- PlaylistWriter -----------------------------------------------------
    def create_playlist(self, title: str, description: str = "") -> str:
        uid = self._me_id()
        data = self._post(
            f"/users/{uid}/playlists",
            json={"name": title, "description": description or "", "public": False},
        )
        return data["id"]

    def add_tracks(self, playlist_id: str, track_ids: list[str]) -> None:
        uris = [f"spotify:track:{t}" for t in track_ids]
        self._post(f"/playlists/{playlist_id}/tracks", json={"uris": uris})

    def remove_track(self, playlist_id: str, track_id: str) -> None:
        self._delete(
            f"/playlists/{playlist_id}/tracks",
            json={"tracks": [{"uri": f"spotify:track:{track_id}"}]},
        )

    def edit_playlist(self, playlist_id: str, title: str | None, description: str | None) -> None:
        body: dict[str, Any] = {}
        if title is not None:
            body["name"] = title
        if description is not None:
            body["description"] = description
        if body:
            self._put(f"/playlists/{playlist_id}", json=body)

    def delete_playlist(self, playlist_id: str) -> None:
        # Spotify has no delete; unfollowing your own playlist removes it from the library.
        self._delete(f"/playlists/{playlist_id}/followers")

    def artist_top_tracks(self, artist_id: str, limit: int = 1) -> list[str]:
        data = self._get(f"/artists/{artist_id}/top-tracks", {"market": "from_token"})
        return [t["id"] for t in data.get("tracks", [])[:limit]]

    def get_artist_name(self, artist_id: str) -> Optional[str]:
        try:
            return self._get(f"/artists/{artist_id}").get("name")
        except Exception:
            return None

    # ---- MusicGateway -------------------------------------------------------
    def fetch_library_snapshot(self) -> LibrarySnapshot:
        snap = LibrarySnapshot()
        artists: dict[str, Artist] = {}
        albums: dict[str, Album] = {}
        tracks: dict[str, Track] = {}

        def remember(t: dict) -> Optional[str]:
            if not t or not t.get("id"):
                return None
            for a in t.get("artists", []):
                if a.get("id"):
                    artists.setdefault(a["id"], _artist(a))
            al = t.get("album")
            if al and al.get("id"):
                albums.setdefault(al["id"], _album(al))
            tracks[t["id"]] = _track(t)
            return t["id"]

        # Playlists + ordered tracks.
        for pl in self._paginate("/me/playlists", {"limit": 50}):
            snap.playlists.append(_playlist(pl))
            ids: list[str] = []
            for item in self._paginate(f"/playlists/{pl['id']}/tracks", {"limit": 100}):
                tid = remember((item or {}).get("track") or {})
                if tid:
                    ids.append(tid)
            snap.playlist_tracks[pl["id"]] = ids

        # Saved tracks / albums / followed artists.
        for item in self._paginate("/me/tracks", {"limit": 50}):
            tid = remember((item or {}).get("track") or {})
            if tid:
                snap.favorite_track_ids.append(tid)
        for item in self._paginate("/me/albums", {"limit": 50}):
            al = (item or {}).get("album") or {}
            if al.get("id"):
                albums.setdefault(al["id"], _album(al))
                snap.favorite_album_ids.append(al["id"])
        for a in self._paginate_artists():
            if a.get("id"):
                artists.setdefault(a["id"], _artist(a))
                snap.favorite_artist_ids.append(a["id"])

        snap.artists = list(artists.values())
        snap.albums = list(albums.values())
        snap.tracks = list(tracks.values())
        return snap

    def fetch_playlist(self, playlist_id: str) -> LibrarySnapshot:
        snap = LibrarySnapshot()
        artists: dict[str, Artist] = {}
        albums: dict[str, Album] = {}
        tracks: dict[str, Track] = {}
        meta = self._get(f"/playlists/{playlist_id}")
        snap.playlists.append(_playlist(meta))
        ids: list[str] = []
        for item in self._paginate(f"/playlists/{playlist_id}/tracks", {"limit": 100}):
            t = (item or {}).get("track") or {}
            if not t.get("id"):
                continue
            for a in t.get("artists", []):
                if a.get("id"):
                    artists.setdefault(a["id"], _artist(a))
            al = t.get("album")
            if al and al.get("id"):
                albums.setdefault(al["id"], _album(al))
            tracks[t["id"]] = _track(t)
            ids.append(t["id"])
        snap.playlist_tracks[playlist_id] = ids
        snap.artists = list(artists.values())
        snap.albums = list(albums.values())
        snap.tracks = list(tracks.values())
        return snap

    # ---- internals ----------------------------------------------------------
    def _apply_token(self, payload: dict) -> None:
        self._access = payload["access_token"]
        if payload.get("refresh_token"):
            self._refresh = payload["refresh_token"]
        self._expiry = datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 3600)))

    def _ensure_token(self) -> None:
        if not self._access:
            raise RuntimeError("Not connected to Spotify")
        if self._expiry and datetime.now(timezone.utc) < self._expiry - timedelta(seconds=60):
            return
        if not self._refresh:
            return
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh,
                "client_id": SPOTIFY_CLIENT_ID,
            },
            timeout=15,
        )
        resp.raise_for_status()
        self._apply_token(resp.json())

    def _headers(self) -> dict:
        self._ensure_token()
        return {"Authorization": f"Bearer {self._access}"}

    def _request(self, method: str, path: str, params=None, json=None) -> Any:
        url = path if path.startswith("http") else API + path
        resp = requests.request(method, url, headers=self._headers(), params=params, json=json, timeout=30)
        if resp.status_code == 401:  # token edge — refresh once and retry
            self._expiry = None
            resp = requests.request(method, url, headers=self._headers(), params=params, json=json, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"Spotify {method} {path} -> {resp.status_code}: {resp.text[:200]}")
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def _get(self, path, params=None):
        return self._request("GET", path, params=params)

    def _post(self, path, params=None, json=None):
        return self._request("POST", path, params=params, json=json)

    def _put(self, path, params=None, json=None):
        return self._request("PUT", path, params=params, json=json)

    def _delete(self, path, params=None, json=None):
        return self._request("DELETE", path, params=params, json=json)

    def _paginate(self, path: str, params: dict) -> list[dict]:
        out: list[dict] = []
        data = self._get(path, params)
        while True:
            out.extend(data.get("items", []))
            nxt = data.get("next")
            if not nxt:
                break
            data = self._get(nxt)
        return out

    def _paginate_artists(self) -> list[dict]:
        # Followed artists use cursor pagination under an `artists` envelope.
        out: list[dict] = []
        data = self._get("/me/following", {"type": "artist", "limit": 50})
        while True:
            block = data.get("artists", {})
            out.extend(block.get("items", []))
            nxt = block.get("next")
            if not nxt:
                break
            data = self._get(nxt)
        return out

    def _me_id(self) -> str:
        if not self._user_id:
            self._fetch_me()
        if not self._user_id:
            raise RuntimeError("Not connected to Spotify")
        return self._user_id

    def _fetch_me(self) -> Optional[str]:
        try:
            me = self._get("/me")
            self._user_id = me.get("id")
            self._user_name = me.get("display_name") or me.get("id")
            return self._user_name
        except Exception:
            return None


# ---- mapping: Spotify JSON -> domain entity ----

def _img(images: list[dict] | None) -> Optional[str]:
    return images[0]["url"] if images else None


def _artist(a: dict) -> Artist:
    return Artist(id=a["id"], name=a.get("name", ""), picture=_img(a.get("images")))


def _album(al: dict) -> Album:
    artists = al.get("artists") or []
    first = artists[0] if artists else {}
    return Album(
        id=al["id"],
        title=al.get("name", ""),
        artist_id=first.get("id"),
        artist_name=first.get("name"),
        cover=_img(al.get("images")),
        num_tracks=al.get("total_tracks"),
        release_date=al.get("release_date"),
    )


def _track(t: dict) -> Track:
    artists = t.get("artists") or []
    first = artists[0] if artists else {}
    al = t.get("album") or {}
    dur = t.get("duration_ms")
    return Track(
        id=t["id"],
        title=t.get("name", ""),
        duration=int(dur / 1000) if dur else None,
        artist_id=first.get("id"),
        artist_name=first.get("name"),
        album_id=al.get("id"),
        album_title=al.get("name"),
        isrc=(t.get("external_ids") or {}).get("isrc"),
    )


def _playlist(pl: dict) -> Playlist:
    owner = pl.get("owner") or {}
    tracks = pl.get("tracks") or {}
    return Playlist(
        id=pl["id"],
        title=pl.get("name", ""),
        description=pl.get("description"),
        num_tracks=tracks.get("total", 0) or 0,
        creator=owner.get("display_name") or owner.get("id"),
        picture=_img(pl.get("images")),
        last_updated=None,
    )
