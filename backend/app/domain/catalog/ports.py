"""Catalog ports."""
from __future__ import annotations

from typing import Protocol

from .entities import CatalogSearchResults


class CatalogGateway(Protocol):
    """Searches the music service's catalog."""

    def search(self, query: str, include: list[str]) -> CatalogSearchResults:
        """Search the catalog. `include` is any of: artists, albums, tracks."""
