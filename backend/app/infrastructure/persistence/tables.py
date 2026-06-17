"""SQLModel tables — the persistence representation, kept separate from domain
entities. Tidal ids are primary keys so re-import upserts in place.
"""
from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class ArtistRow(SQLModel, table=True):
    __tablename__ = "artist"
    id: int = Field(primary_key=True)
    name: str
    picture: Optional[str] = None


class AlbumRow(SQLModel, table=True):
    __tablename__ = "album"
    id: int = Field(primary_key=True)
    title: str
    artist_id: Optional[int] = None
    artist_name: Optional[str] = None
    cover: Optional[str] = None
    num_tracks: Optional[int] = None
    release_date: Optional[str] = None


class TrackRow(SQLModel, table=True):
    __tablename__ = "track"
    id: int = Field(primary_key=True)
    title: str
    duration: Optional[int] = None
    artist_id: Optional[int] = None
    artist_name: Optional[str] = None
    album_id: Optional[int] = None
    album_title: Optional[str] = None
    isrc: Optional[str] = None


class PlaylistRow(SQLModel, table=True):
    __tablename__ = "playlist"
    id: str = Field(primary_key=True)
    title: str
    description: Optional[str] = None
    num_tracks: int = 0
    creator: Optional[str] = None
    picture: Optional[str] = None
    last_updated: Optional[str] = None


class PlaylistTrackRow(SQLModel, table=True):
    __tablename__ = "playlist_track"
    playlist_id: str = Field(primary_key=True)
    position: int = Field(primary_key=True)
    track_id: int


class FavoriteRow(SQLModel, table=True):
    __tablename__ = "favorite"
    item_type: str = Field(primary_key=True)
    item_id: str = Field(primary_key=True)
