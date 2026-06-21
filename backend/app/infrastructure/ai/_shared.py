"""Shared prompt building and pick->Recommendation mapping for LLM curators."""
from __future__ import annotations

from ...domain.discovery.entities import Candidate, Recommendation, TasteProfile

SYSTEM = (
    "You are a music curator. Given a listener's taste (a set of artists they love) "
    "and a pool of candidate artists already known to be sonically related, select and "
    "rank the candidates that best fit their taste and would be genuinely exciting "
    "discoveries. For each pick, write one concise, specific sentence on why it fits — "
    "reference the listener's actual seed artists or the musical qualities they share. "
    "Only choose from the provided candidates; never invent artists or ids."
)

# JSON Schema for the structured response (used by Ollama; Anthropic uses Pydantic).
PICKS_SCHEMA = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "artist_id": {"type": "string"},
                    "name": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["artist_id", "name", "reason"],
            },
        }
    },
    "required": ["picks"],
}


def build_user_prompt(profile: TasteProfile, candidates: list[Candidate], limit: int) -> str:
    seeds = ", ".join(profile.seed_artist_names) or "(unknown)"
    candidate_lines = "\n".join(
        f"- id={c.artist_id} | {c.name} | related_to_{c.score}_of_your_artists"
        for c in candidates
    )
    return (
        f"The listener loves these artists:\n{seeds}\n\n"
        f"Candidate artists to choose from:\n{candidate_lines}\n\n"
        f"Pick up to {limit} candidates, ranked best-fit first. "
        f"Respond as JSON: {{\"picks\": [{{\"artist_id\": str, \"name\": str, \"reason\": str}}]}}."
    )


def picks_to_recommendations(picks: list[dict], candidates: list[Candidate]) -> list[Recommendation]:
    """Map model picks back to candidates, dropping any id outside the pool (stays grounded)."""
    by_id = {c.artist_id: c for c in candidates}
    out: list[Recommendation] = []
    for pick in picks:
        aid = pick.get("artist_id")
        if aid is None:
            continue
        candidate = by_id.get(str(aid))
        if candidate is None:
            continue
        reason = str(pick.get("reason") or "").strip()
        out.append(
            Recommendation(
                artist_id=candidate.artist_id,
                name=candidate.name,
                reason=reason or f"Related to {candidate.score} of your favorite artists.",
                score=candidate.score,
            )
        )
    return out
