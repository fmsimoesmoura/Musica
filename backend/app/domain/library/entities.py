"""Library domain entities — pure data, no framework or SDK imports.

These model the user's *owned* music data (playlists + favorites). They are
independent of how Tidal returns them or how we persist them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Artist:
    id: str
    name: str
    picture: Optional[str] = None


@dataclass
class Album:
    id: str
    title: str
    artist_id: Optional[str] = None
    artist_name: Optional[str] = None
    cover: Optional[str] = None
    num_tracks: Optional[int] = None
    release_date: Optional[str] = None


@dataclass
class Track:
    id: str
    title: str
    duration: Optional[int] = None
    artist_id: Optional[str] = None
    artist_name: Optional[str] = None
    album_id: Optional[str] = None
    album_title: Optional[str] = None
    isrc: Optional[str] = None
    image: Optional[str] = None  # album-cover URL, for display in track lists
    explicit: Optional[bool] = None


@dataclass
class Playlist:
    id: str
    title: str
    description: Optional[str] = None
    num_tracks: int = 0
    creator: Optional[str] = None
    picture: Optional[str] = None
    last_updated: Optional[str] = None


@dataclass
class LibrarySnapshot:
    """A complete read of the user's library at a point in time.

    The Tidal gateway produces this; the repository persists it. Keeping it as a
    single aggregate lets the import run as one atomic transaction.
    """

    artists: list[Artist] = field(default_factory=list)
    albums: list[Album] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=list)
    playlists: list[Playlist] = field(default_factory=list)
    # playlist id -> ordered list of track ids
    playlist_tracks: dict[str, list[str]] = field(default_factory=dict)
    favorite_track_ids: list[str] = field(default_factory=list)
    favorite_artist_ids: list[str] = field(default_factory=list)
    favorite_album_ids: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "playlists": len(self.playlists),
            "playlist_tracks": sum(len(v) for v in self.playlist_tracks.values()),
            "fav_tracks": len(self.favorite_track_ids),
            "fav_artists": len(self.favorite_artist_ids),
            "fav_albums": len(self.favorite_album_ids),
        }
