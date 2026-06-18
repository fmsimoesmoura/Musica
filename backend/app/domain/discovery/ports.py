"""Discovery ports."""
from __future__ import annotations

from typing import Protocol

from ..library.entities import Artist
from .entities import Candidate, Recommendation, TasteProfile


class RecommendationGateway(Protocol):
    """Surfaces candidate artists from the music service (Tidal radio/similar)."""

    def similar_artists(self, artist_id: int) -> list[Artist]:
        ...

    def artist_top_tracks(self, artist_id: int, limit: int = 1) -> list[int]:
        """Top track ids for an artist — used to seed a playlist from picks."""
        ...


class Curator(Protocol):
    """Ranks candidates against the user's taste and explains the fit (AI)."""

    def curate(
        self, profile: TasteProfile, candidates: list[Candidate], limit: int
    ) -> list[Recommendation]:
        ...
