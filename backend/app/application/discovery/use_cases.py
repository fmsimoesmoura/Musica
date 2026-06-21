"""Discovery use case — the hybrid engine.

Flow: seed from favorite artists -> Tidal similar-artists for candidates ->
filter out everything already in the library -> Claude ranks & explains fit.
"""
from __future__ import annotations

import logging

from ...domain.discovery.entities import Candidate, DiscoveryResult, TasteProfile
from ...domain.discovery.ports import Curator, RecommendationGateway
from ...domain.library.ports import LibraryRepository

log = logging.getLogger("app.discovery")

_DEFAULT_SEEDS = 12
_CANDIDATE_POOL = 40


class GenerateRecommendations:
    def __init__(
        self,
        repository: LibraryRepository,
        gateway: RecommendationGateway,
        curator: Curator,
    ):
        self._repository = repository
        self._gateway = gateway
        self._curator = curator

    def __call__(self, max_recommendations: int = 12, seed_count: int = _DEFAULT_SEEDS) -> DiscoveryResult:
        if self._gateway is None:
            return DiscoveryResult(note="Discovery isn't available for this provider.")
        favorites = self._repository.list_favorite_artists()
        if not favorites:
            return DiscoveryResult(
                note="No favorite artists found. Import your library first to seed discovery."
            )

        known = self._repository.all_artist_ids()
        seeds = favorites[:seed_count]

        # Aggregate similar artists across seeds; frequency = fit strength.
        candidates: dict[str, Candidate] = {}
        for seed in seeds:
            try:
                similar = self._gateway.similar_artists(seed.id)
            except Exception as e:
                log.warning("similar_artists failed for %s: %s", seed.name, e)
                continue
            for artist in similar:
                aid = artist.id
                if aid in known:
                    continue
                if aid in candidates:
                    candidates[aid].score += 1
                else:
                    candidates[aid] = Candidate(artist_id=aid, name=artist.name, score=1)

        if not candidates:
            return DiscoveryResult(
                based_on=[s.name for s in seeds],
                note="Couldn't find new artists from your favorites right now. Try re-syncing or adding more favorites.",
            )

        pool = sorted(candidates.values(), key=lambda c: c.score, reverse=True)[:_CANDIDATE_POOL]
        profile = TasteProfile(seed_artist_names=[s.name for s in seeds])
        recommendations = self._curator.curate(profile, pool, max_recommendations)
        return DiscoveryResult(
            recommendations=recommendations,
            based_on=profile.seed_artist_names,
        )
