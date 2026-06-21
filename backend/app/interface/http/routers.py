"""FastAPI routers — thin HTTP adapters over use cases. No business logic here."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ...composition import container, list_providers, switch_provider
from .dto import to_list


class CreatePlaylistBody(BaseModel):
    title: str
    description: str = ""


class EditPlaylistBody(BaseModel):
    title: str | None = None
    description: str | None = None


class AddTracksBody(BaseModel):
    track_ids: list[str]


class SaveDiscoveryBody(BaseModel):
    name: str
    artist_ids: list[str]
    tracks_per_artist: int = 1


class ActiveProviderBody(BaseModel):
    provider: str


class CredentialsBody(BaseModel):
    username: str
    password: str

auth = APIRouter(prefix="/auth", tags=["auth"])
lib = APIRouter(tags=["library"])
catalog = APIRouter(tags=["catalog"])
discovery = APIRouter(tags=["discovery"])
providers = APIRouter(tags=["providers"])


@providers.get("/providers")
def get_providers():
    return list_providers()


@providers.post("/providers/active")
def set_provider(body: ActiveProviderBody):
    try:
        switch_provider(body.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"active": body.provider}


@auth.post("/start")
def auth_start():
    try:
        return asdict(container().connect.start())
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth.get("/poll")
def auth_poll(login_id: str = Query(...)):
    result = container().connect.poll(login_id)
    return {
        "status": result.status.value,
        "connected": result.connected,
        "user_name": result.user_name,
    }


@auth.get("/status")
def auth_status():
    return asdict(container().get_status())


@auth.post("/logout")
def auth_logout():
    container().logout()
    return {"connected": False}


@auth.post("/credentials")
def auth_credentials(body: CredentialsBody):
    """Username/password login for providers without a browser flow (e.g. Qobuz)."""
    c = container()
    login = getattr(c.auth, "login_with_credentials", None)
    if login is None:
        raise HTTPException(status_code=400, detail="Active provider does not support password login")
    try:
        ok = login(body.username, body.password)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=401, detail="Login failed — check your credentials")
    tokens = c.auth.current_tokens()
    if tokens:
        c.token_store.save(tokens)
    status = c.get_status()
    return {"connected": status.connected, "user_name": status.user_name}


@auth.get("/spotify/callback", response_class=HTMLResponse)
def spotify_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    """Spotify Authorization-Code redirect target. Hands the code to the gateway."""
    gw = container().auth
    handler = getattr(gw, "handle_callback", None)
    if handler is None:
        raise HTTPException(status_code=400, detail="Active provider is not Spotify")
    ok = handler(code=code, state=state, error=error)
    msg = "Spotify connected — you can close this tab." if ok else f"Login failed: {error or 'unknown error'}"
    return f"<html><body style='font-family:sans-serif;padding:2rem'>{msg}</body></html>"


def _require_connection() -> None:
    if not container().get_status().connected:
        raise HTTPException(status_code=401, detail="Not connected to Tidal")


@lib.post("/library/import")
def library_import():
    _require_connection()
    return container().import_library()


@lib.get("/playlists")
def get_playlists():
    return to_list(container().get_playlists())


@lib.get("/playlists/{playlist_id}/tracks")
def get_playlist_tracks(playlist_id: str):
    return to_list(container().get_playlist_tracks(playlist_id))


@lib.get("/favorites")
def get_favorites(type: str = Query("tracks")):
    item_type = type.rstrip("s")  # tracks -> track
    return to_list(container().get_favorites(item_type))


# ---- playlist write (M4) ----

@lib.post("/playlists")
def create_playlist(body: CreatePlaylistBody):
    _require_connection()
    pid = container().manage_playlists.create(body.title, body.description)
    return {"playlist_id": pid}


@lib.patch("/playlists/{playlist_id}")
def edit_playlist(playlist_id: str, body: EditPlaylistBody):
    _require_connection()
    container().manage_playlists.rename(playlist_id, body.title, body.description)
    return {"ok": True}


@lib.delete("/playlists/{playlist_id}")
def delete_playlist(playlist_id: str):
    _require_connection()
    container().manage_playlists.delete(playlist_id)
    return {"ok": True}


@lib.post("/playlists/{playlist_id}/tracks")
def add_tracks(playlist_id: str, body: AddTracksBody):
    _require_connection()
    container().manage_playlists.add_tracks(playlist_id, body.track_ids)
    return {"ok": True}


@lib.delete("/playlists/{playlist_id}/tracks/{track_id}")
def remove_track(playlist_id: str, track_id: str):
    _require_connection()
    container().manage_playlists.remove_track(playlist_id, track_id)
    return {"ok": True}


@catalog.get("/search")
def search(q: str = Query(...), include: str = Query("artists,albums,tracks")):
    _require_connection()
    wanted = [p.strip() for p in include.split(",") if p.strip()]
    results = container().search_catalog(q, wanted)
    return {
        "artists": to_list(results.artists),
        "albums": to_list(results.albums),
        "tracks": to_list(results.tracks),
    }


@catalog.post("/favorites/{item_type}/{item_id}")
def add_favorite(item_type: str, item_id: str):
    _require_connection()
    try:
        return {"ok": container().set_favorite.add(item_type, item_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@catalog.delete("/favorites/{item_type}/{item_id}")
def remove_favorite(item_type: str, item_id: str):
    _require_connection()
    try:
        return {"ok": container().set_favorite.remove(item_type, item_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@discovery.get("/discover/backend")
def discover_backend():
    return {"backend": container().curator_backend}


@discovery.post("/discover")
def discover(limit: int = Query(12, ge=1, le=30)):
    _require_connection()
    try:
        result = container().generate_recommendations(max_recommendations=limit)
    except RuntimeError as e:
        # e.g. missing key, Ollama not running, or an AI provider error.
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "based_on": result.based_on,
        "note": result.note,
        "backend": container().curator_backend,
        "recommendations": to_list(result.recommendations),
    }


@discovery.post("/discover/save")
def save_discovery(body: SaveDiscoveryBody):
    _require_connection()
    return container().save_recommendations(
        body.name, body.artist_ids, body.tracks_per_artist
    )
