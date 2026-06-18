"""Composition root — the single place that wires concrete adapters into use
cases. Nothing else constructs infrastructure. Swap an implementation here and
the rest of the app is untouched.
"""
from __future__ import annotations

from functools import lru_cache

from .application.auth.use_cases import ConnectTidal, GetStatus, Logout, RestoreSession
from .application.catalog.use_cases import SearchCatalog
from .application.discovery.use_cases import GenerateRecommendations
from .application.library.use_cases import (
    GetFavorites,
    GetPlaylists,
    GetPlaylistTracks,
    ImportLibrary,
    SetFavorite,
)
from .infrastructure.ai.curator import AnthropicCurator
from .infrastructure.persistence.repository import SqliteLibraryRepository
from .infrastructure.security.token_store import KeyringTokenStore
from .infrastructure.tidal.gateway import TidalApiGateway


class Container:
    def __init__(self) -> None:
        # Adapters (single instances for the process lifetime).
        self.tidal = TidalApiGateway()
        self.token_store = KeyringTokenStore()
        self.repository = SqliteLibraryRepository()
        self.curator = AnthropicCurator()

        # Use cases.
        self.connect = ConnectTidal(self.tidal, self.token_store)
        self.restore_session = RestoreSession(self.tidal, self.token_store)
        self.get_status = GetStatus(self.tidal)
        self.logout = Logout(self.tidal, self.token_store)

        self.import_library = ImportLibrary(self.tidal, self.repository)
        self.get_playlists = GetPlaylists(self.repository)
        self.get_playlist_tracks = GetPlaylistTracks(self.repository)
        self.get_favorites = GetFavorites(self.repository)

        self.search_catalog = SearchCatalog(self.tidal)
        self.set_favorite = SetFavorite(self.tidal)

        self.generate_recommendations = GenerateRecommendations(
            self.repository, self.tidal, self.curator
        )


@lru_cache(maxsize=1)
def container() -> Container:
    return Container()
