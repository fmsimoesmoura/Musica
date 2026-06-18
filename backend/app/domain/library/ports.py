"""Library ports — interfaces for reading from Tidal and persisting locally."""
from __future__ import annotations

from typing import Protocol

from .entities import Album, Artist, LibrarySnapshot, Playlist, Track


class MusicGateway(Protocol):
    """Reads the user's library from the music service (Tidal)."""

    def fetch_library_snapshot(self) -> LibrarySnapshot:
        """Pull playlists (+ordered tracks) and favorites into a domain snapshot."""

    def fetch_playlist(self, playlist_id: str) -> LibrarySnapshot:
        """Re-read a single playlist (+its tracks) for local refresh after a write."""


class PlaylistWriter(Protocol):
    """Mutates the user's playlists on the music service."""

    def create_playlist(self, title: str, description: str = "") -> str:
        """Create a playlist; returns its new id."""

    def add_tracks(self, playlist_id: str, track_ids: list[int]) -> None:
        ...

    def remove_track(self, playlist_id: str, track_id: int) -> None:
        ...

    def edit_playlist(self, playlist_id: str, title: str | None, description: str | None) -> None:
        ...

    def delete_playlist(self, playlist_id: str) -> None:
        ...


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

    def all_artist_ids(self) -> set[int]:
        """Every artist id present in the imported library (favorites + playlists).

        Used by discovery to filter out artists the user already knows.
        """
        ...

    def save_playlist_snapshot(self, snapshot: LibrarySnapshot) -> None:
        """Upsert the playlists in `snapshot` (+their tracks/ordering) WITHOUT
        touching favorites or other playlists. Used to refresh one edited playlist."""
        ...

    def delete_playlist(self, playlist_id: str) -> None:
        """Remove a playlist and its track ordering from the local DB."""
        ...
