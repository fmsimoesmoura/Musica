"""NoLlmCurator — zero-dependency fallback. Ranks purely by Tidal similarity
score (how many of the user's favorites each candidate relates to) and writes a
templated reason. No external calls, no keys, instant.
"""
from __future__ import annotations

from ...domain.discovery.entities import Candidate, Recommendation, TasteProfile


class NoLlmCurator:
    backend_name = "none"

    def curate(
        self, profile: TasteProfile, candidates: list[Candidate], limit: int
    ) -> list[Recommendation]:
        ranked = sorted(candidates, key=lambda c: c.score, reverse=True)[:limit]
        return [
            Recommendation(
                artist_id=c.artist_id,
                name=c.name,
                reason=(
                    f"Related to {c.score} of your favorite artists"
                    f"{' — a strong match' if c.score > 1 else ''}."
                ),
                score=c.score,
            )
            for c in ranked
        ]
