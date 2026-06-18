"""SqliteLibraryRepository — implements the LibraryRepository port over SQLModel.

Translates between domain entities and persistence rows. All snapshot writes
happen in a single transaction.
"""
from __future__ import annotations

from sqlmodel import Session, select

from ...domain.library.entities import (
    Album,
    Artist,
    LibrarySnapshot,
    Playlist,
    Track,
)
from .db import engine
from .tables import (
    AlbumRow,
    ArtistRow,
    FavoriteRow,
    PlaylistRow,
    PlaylistTrackRow,
    TrackRow,
)


class SqliteLibraryRepository:
    # ---- write ----
    def save_snapshot(self, snapshot: LibrarySnapshot) -> None:
        with Session(engine) as session:
            for a in snapshot.artists:
                session.merge(_artist_row(a))
            for al in snapshot.albums:
                session.merge(_album_row(al))
            for t in snapshot.tracks:
                session.merge(_track_row(t))

            for pl in snapshot.playlists:
                session.merge(_playlist_row(pl))

            # Replace playlist orderings and favorites wholesale.
            for pid, track_ids in snapshot.playlist_tracks.items():
                for old in session.exec(
                    select(PlaylistTrackRow).where(PlaylistTrackRow.playlist_id == pid)
                ).all():
                    session.delete(old)
                for pos, tid in enumerate(track_ids):
                    session.add(PlaylistTrackRow(playlist_id=pid, position=pos, track_id=tid))

            for old_fav in session.exec(select(FavoriteRow)).all():
                session.delete(old_fav)
            for tid in snapshot.favorite_track_ids:
                session.add(FavoriteRow(item_type="track", item_id=str(tid)))
            for aid in snapshot.favorite_artist_ids:
                session.add(FavoriteRow(item_type="artist", item_id=str(aid)))
            for alid in snapshot.favorite_album_ids:
                session.add(FavoriteRow(item_type="album", item_id=str(alid)))

            session.commit()

    # ---- read ----
    def list_playlists(self) -> list[Playlist]:
        with Session(engine) as session:
            return [_playlist_entity(r) for r in session.exec(select(PlaylistRow)).all()]

    def list_playlist_tracks(self, playlist_id: str) -> list[Track]:
        with Session(engine) as session:
            pts = session.exec(
                select(PlaylistTrackRow)
                .where(PlaylistTrackRow.playlist_id == playlist_id)
                .order_by(PlaylistTrackRow.position)
            ).all()
            out: list[Track] = []
            for pt in pts:
                row = session.get(TrackRow, pt.track_id)
                if row:
                    out.append(_track_entity(row))
            return out

    def list_favorite_tracks(self) -> list[Track]:
        return self._favorites(TrackRow, "track", _track_entity)

    def list_favorite_artists(self) -> list[Artist]:
        return self._favorites(ArtistRow, "artist", _artist_entity)

    def list_favorite_albums(self) -> list[Album]:
        return self._favorites(AlbumRow, "album", _album_entity)

    def all_artist_ids(self) -> set[int]:
        with Session(engine) as session:
            return set(session.exec(select(ArtistRow.id)).all())

    def save_playlist_snapshot(self, snapshot: LibrarySnapshot) -> None:
        # Partial upsert: only the playlists in the snapshot; favorites untouched.
        with Session(engine) as session:
            for a in snapshot.artists:
                session.merge(_artist_row(a))
            for al in snapshot.albums:
                session.merge(_album_row(al))
            for t in snapshot.tracks:
                session.merge(_track_row(t))
            for pl in snapshot.playlists:
                session.merge(_playlist_row(pl))
            for pid, track_ids in snapshot.playlist_tracks.items():
                for old in session.exec(
                    select(PlaylistTrackRow).where(PlaylistTrackRow.playlist_id == pid)
                ).all():
                    session.delete(old)
                for pos, tid in enumerate(track_ids):
                    session.add(PlaylistTrackRow(playlist_id=pid, position=pos, track_id=tid))
            session.commit()

    def delete_playlist(self, playlist_id: str) -> None:
        with Session(engine) as session:
            for pt in session.exec(
                select(PlaylistTrackRow).where(PlaylistTrackRow.playlist_id == playlist_id)
            ).all():
                session.delete(pt)
            row = session.get(PlaylistRow, playlist_id)
            if row:
                session.delete(row)
            session.commit()

    def _favorites(self, row_model, item_type: str, to_entity):
        with Session(engine) as session:
            favs = session.exec(
                select(FavoriteRow).where(FavoriteRow.item_type == item_type)
            ).all()
            out = []
            for f in favs:
                row = session.get(row_model, int(f.item_id))
                if row:
                    out.append(to_entity(row))
            return out


# ---- mapping: domain entity <-> persistence row ----

def _artist_row(a: Artist) -> ArtistRow:
    return ArtistRow(id=a.id, name=a.name, picture=a.picture)


def _album_row(a: Album) -> AlbumRow:
    return AlbumRow(
        id=a.id, title=a.title, artist_id=a.artist_id, artist_name=a.artist_name,
        cover=a.cover, num_tracks=a.num_tracks, release_date=a.release_date,
    )


def _track_row(t: Track) -> TrackRow:
    return TrackRow(
        id=t.id, title=t.title, duration=t.duration, artist_id=t.artist_id,
        artist_name=t.artist_name, album_id=t.album_id, album_title=t.album_title, isrc=t.isrc,
    )


def _playlist_row(p: Playlist) -> PlaylistRow:
    return PlaylistRow(
        id=p.id, title=p.title, description=p.description, num_tracks=p.num_tracks,
        creator=p.creator, picture=p.picture, last_updated=p.last_updated,
    )


def _artist_entity(r: ArtistRow) -> Artist:
    return Artist(id=r.id, name=r.name, picture=r.picture)


def _album_entity(r: AlbumRow) -> Album:
    return Album(
        id=r.id, title=r.title, artist_id=r.artist_id, artist_name=r.artist_name,
        cover=r.cover, num_tracks=r.num_tracks, release_date=r.release_date,
    )


def _track_entity(r: TrackRow) -> Track:
    return Track(
        id=r.id, title=r.title, duration=r.duration, artist_id=r.artist_id,
        artist_name=r.artist_name, album_id=r.album_id, album_title=r.album_title, isrc=r.isrc,
    )


def _playlist_entity(r: PlaylistRow) -> Playlist:
    return Playlist(
        id=r.id, title=r.title, description=r.description, num_tracks=r.num_tracks,
        creator=r.creator, picture=r.picture, last_updated=r.last_updated,
    )
