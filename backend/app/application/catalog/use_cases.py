"""Catalog use cases."""
from __future__ import annotations

from ...domain.catalog.entities import CatalogSearchResults
from ...domain.catalog.ports import CatalogGateway

_VALID_INCLUDE = ("artists", "albums", "tracks")


class SearchCatalog:
    def __init__(self, gateway: CatalogGateway):
        self._gateway = gateway

    def __call__(self, query: str, include: list[str] | None = None) -> CatalogSearchResults:
        query = (query or "").strip()
        if not query:
            return CatalogSearchResults()
        wanted = [i for i in (include or _VALID_INCLUDE) if i in _VALID_INCLUDE]
        return self._gateway.search(query, wanted or list(_VALID_INCLUDE))
