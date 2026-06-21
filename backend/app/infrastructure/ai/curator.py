"""AnthropicCurator — ranks candidate artists and explains the fit using Claude.

Uses structured outputs (messages.parse + Pydantic) so the model returns
validated, typed picks. The only module that imports the Anthropic SDK.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from ...config import ANTHROPIC_API_KEY, DISCOVERY_MODEL
from ...domain.discovery.entities import Candidate, Recommendation, TasteProfile
from ._shared import SYSTEM, build_user_prompt, picks_to_recommendations

log = logging.getLogger("infra.ai")


class _Pick(BaseModel):
    artist_id: str
    name: str
    reason: str


class _Curation(BaseModel):
    picks: list[_Pick]


class AnthropicCurator:
    backend_name = "anthropic"

    def __init__(self) -> None:
        self._model = DISCOVERY_MODEL

    def curate(
        self, profile: TasteProfile, candidates: list[Candidate], limit: int
    ) -> list[Recommendation]:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to backend/.env to enable AI-curated discovery."
            )
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        try:
            response = client.messages.parse(
                model=self._model,
                max_tokens=4000,
                system=SYSTEM,
                messages=[{"role": "user", "content": build_user_prompt(profile, candidates, limit)}],
                output_format=_Curation,
            )
        except anthropic.APIStatusError as e:
            log.warning("Anthropic curation failed: %s", e)
            raise RuntimeError(f"AI curation failed: {e.message}") from e

        curation = response.parsed_output
        if curation is None:
            return []
        picks = [{"artist_id": p.artist_id, "name": p.name, "reason": p.reason} for p in curation.picks]
        return picks_to_recommendations(picks, candidates)
