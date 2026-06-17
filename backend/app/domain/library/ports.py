"""Library ports — interfaces for reading from Tidal and persisting locally."""
from __future__ import annotations

from typing import Protocol

from .entities import Album, Artist, LibrarySnapshot, Playlist, Track


class MusicGateway(Protocol):
    """Reads the user's library from the music service (Tidal)."""

    def fetch_library_snapshot(self) -> LibrarySnapshot:
        """Pull playlists (+ordered tracks) and favorites into a domain snapshot."""


class FavoritesGateway(Protocol):
    """Mutates the user's favorites on the music service."""

    def add(self, item_type: str, item_id: str) -> bool:
        """item_type is one of: track | artist | album."""

    def remove(self, item_type: str, item_id: str) -> bool:
        ...


class LibraryRepository(Protocol):
    """Local persistence of the imported library."""

    def save_snapshot(self, snapshot: LibrarySnapshot) -> None:
        """Persist a full snapshot atomically (idempotent upsert)."""

    def list_playlists(self) -> list[Playlist]:
        ...

    def list_playlist_tracks(self, playlist_id: str) -> list[Track]:
        ...

    def list_favorite_tracks(self) -> list[Track]:
        ...

    def list_favorite_artists(self) -> list[Artist]:
        ...

    def list_favorite_albums(self) -> list[Album]:
        ...
