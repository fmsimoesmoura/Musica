"""FastAPI routers — thin HTTP adapters over use cases. No business logic here."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from ...composition import container
from .dto import to_list

auth = APIRouter(prefix="/auth", tags=["auth"])
lib = APIRouter(tags=["library"])
catalog = APIRouter(tags=["catalog"])


@auth.post("/start")
def auth_start():
    return asdict(container().connect.start())


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
