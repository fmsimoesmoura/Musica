"""Discovery domain entities — pure data."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TasteProfile:
    """A lightweight summary of the user's taste used to seed discovery."""

    seed_artist_names: list[str] = field(default_factory=list)


@dataclass
class Candidate:
    """A new artist surfaced by the recommendation engine, not yet in the library."""

    artist_id: int
    name: str
    # How many seed artists this candidate was 'similar to' — a fit-strength signal.
    score: int = 1


@dataclass
class Recommendation:
    artist_id: int
    name: str
    reason: str
    score: int = 1


@dataclass
class DiscoveryResult:
    recommendations: list[Recommendation] = field(default_factory=list)
    based_on: list[str] = field(default_factory=list)
    # A human-readable note when results are empty (e.g. library not imported).
    note: str | None = None
