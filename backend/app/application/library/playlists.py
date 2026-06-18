"""Playlist write use cases.

Each mutation writes to Tidal, then refreshes just that playlist in the local DB
(via fetch_playlist -> save_playlist_snapshot) so the UI reflects the change
without a full library re-sync.
"""
from __future__ import annotations

from ...domain.library.ports import LibraryRepository, MusicGateway, PlaylistWriter


class ManagePlaylists:
    def __init__(
        self,
        writer: PlaylistWriter,
        music_gateway: MusicGateway,
        repository: LibraryRepository,
    ):
        self._writer = writer
        self._music = music_gateway
        self._repository = repository

    def _refresh(self, playlist_id: str) -> None:
        self._repository.save_playlist_snapshot(self._music.fetch_playlist(playlist_id))

    def create(self, title: str, description: str = "") -> str:
        title = (title or "").strip() or "New playlist"
        playlist_id = self._writer.create_playlist(title, description)
        self._refresh(playlist_id)
        return playlist_id

    def add_tracks(self, playlist_id: str, track_ids: list[int]) -> None:
        if track_ids:
            self._writer.add_tracks(playlist_id, track_ids)
            self._refresh(playlist_id)

    def remove_track(self, playlist_id: str, track_id: int) -> None:
        self._writer.remove_track(playlist_id, track_id)
        self._refresh(playlist_id)

    def rename(self, playlist_id: str, title: str | None, description: str | None) -> None:
        self._writer.edit_playlist(playlist_id, title, description)
        self._refresh(playlist_id)

    def delete(self, playlist_id: str) -> None:
        self._writer.delete_playlist(playlist_id)
        self._repository.delete_playlist(playlist_id)
