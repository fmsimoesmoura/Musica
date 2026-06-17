"""Catalog domain entities.

The catalog context reuses the shared music entities (Artist/Album/Track) from
the library domain — they model the same things — and adds a results aggregate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..library.entities import Album, Artist, Track


@dataclass
class CatalogSearchResults:
    artists: list[Artist] = field(default_factory=list)
    albums: list[Album] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=list)
