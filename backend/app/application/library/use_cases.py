"""Library use cases — import and read the user's library."""
from __future__ import annotations

from ...domain.library.entities import Album, Artist, Playlist, Track
from ...domain.library.ports import FavoritesGateway, LibraryRepository, MusicGateway

_VALID_FAVORITE_TYPES = ("track", "artist", "album")


class ImportLibrary:
    def __init__(self, gateway: MusicGateway, repository: LibraryRepository):
        self._gateway = gateway
        self._repository = repository

    def __call__(self) -> dict[str, int]:
        snapshot = self._gateway.fetch_library_snapshot()
        self._repository.save_snapshot(snapshot)
        return snapshot.counts()


class GetPlaylists:
    def __init__(self, repository: LibraryRepository):
        self._repository = repository

    def __call__(self) -> list[Playlist]:
        return self._repository.list_playlists()


class GetPlaylistTracks:
    def __init__(self, repository: LibraryRepository):
        self._repository = repository

    def __call__(self, playlist_id: str) -> list[Track]:
        return self._repository.list_playlist_tracks(playlist_id)


class GetFavorites:
    def __init__(self, repository: LibraryRepository):
        self._repository = repository

    def __call__(self, item_type: str) -> list[Track] | list[Artist] | list[Album]:
        if item_type == "track":
            return self._repository.list_favorite_tracks()
        if item_type == "artist":
            return self._repository.list_favorite_artists()
        if item_type == "album":
            return self._repository.list_favorite_albums()
        return []


class SetFavorite:
    """Add or remove a favorite on the music service.

    Local persistence is intentionally not updated here — the imported library
    reflects the change on the next re-sync; the UI updates optimistically.
    """

    def __init__(self, gateway: FavoritesGateway):
        self._gateway = gateway

    def add(self, item_type: str, item_id: str) -> bool:
        self._validate(item_type)
        return self._gateway.add(item_type, item_id)

    def remove(self, item_type: str, item_id: str) -> bool:
        self._validate(item_type)
        return self._gateway.remove(item_type, item_id)

    @staticmethod
    def _validate(item_type: str) -> None:
        if item_type not in _VALID_FAVORITE_TYPES:
            raise ValueError(f"invalid favorite type: {item_type}")
