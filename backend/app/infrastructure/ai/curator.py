"""AnthropicCurator — ranks candidate artists and explains the fit using Claude.

The only module that imports the Anthropic SDK. Uses structured outputs
(messages.parse + Pydantic) so the model returns validated, typed picks.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from ...config import ANTHROPIC_API_KEY, DISCOVERY_MODEL
from ...domain.discovery.entities import Candidate, Recommendation, TasteProfile

log = logging.getLogger("infra.ai")


class _Pick(BaseModel):
    artist_id: int
    name: str
    reason: str  # one sentence on why this fits the user's taste


class _Curation(BaseModel):
    picks: list[_Pick]


_SYSTEM = (
    "You are a music curator. Given a listener's taste (a set of artists they love) "
    "and a pool of candidate artists already known to be sonically related, select and "
    "rank the candidates that best fit their taste and would be genuinely exciting "
    "discoveries. For each pick, write one concise, specific sentence on why it fits — "
    "reference the listener's actual seed artists or the musical qualities they share. "
    "Only choose from the provided candidates; never invent artists or ids."
)


class AnthropicCurator:
    def __init__(self) -> None:
        self._model = DISCOVERY_MODEL

    def curate(
        self, profile: TasteProfile, candidates: list[Candidate], limit: int
    ) -> list[Recommendation]:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to backend/.env to enable AI-curated discovery."
            )
        # Imported lazily so the app runs without the SDK configured until discovery is used.
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        seeds = ", ".join(profile.seed_artist_names) or "(unknown)"
        candidate_lines = "\n".join(
            f"- id={c.artist_id} | {c.name} | related_to_{c.score}_of_your_artists"
            for c in candidates
        )
        user = (
            f"The listener loves these artists:\n{seeds}\n\n"
            f"Candidate artists to choose from:\n{candidate_lines}\n\n"
            f"Pick up to {limit} candidates, ranked best-fit first."
        )

        try:
            response = client.messages.parse(
                model=self._model,
                max_tokens=4000,
                system=_SYSTEM,
                messages=[{"role": "user", "content": user}],
                output_format=_Curation,
            )
        except anthropic.APIStatusError as e:
            log.warning("Anthropic curation failed: %s", e)
            raise RuntimeError(f"AI curation failed: {e.message}") from e

        curation = response.parsed_output
        if curation is None:
            return []

        by_id = {c.artist_id: c for c in candidates}
        recommendations: list[Recommendation] = []
        for pick in curation.picks:
            candidate = by_id.get(pick.artist_id)
            if candidate is None:
                # Model returned an id outside the pool — skip to stay grounded.
                continue
            recommendations.append(
                Recommendation(
                    artist_id=candidate.artist_id,
                    name=candidate.name,
                    reason=pick.reason,
                    score=candidate.score,
                )
            )
        return recommendations
