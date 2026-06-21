"""Composition root — wires concrete adapters into use cases, per provider.

A `Container` holds everything for ONE provider. The active provider is persisted
(config.get/set_active_provider); switching rebuilds the container. Use cases are
unchanged — they just receive whichever provider's adapters the container built.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .application.auth.use_cases import ConnectTidal, GetStatus, Logout, RestoreSession
from .application.catalog.use_cases import SearchCatalog
from .application.discovery.save_to_playlist import SaveRecommendationsToPlaylist
from .application.discovery.use_cases import GenerateRecommendations
from .application.library.playlists import ManagePlaylists
from .application.library.use_cases import (
    GetFavorites,
    GetPlaylists,
    GetPlaylistTracks,
    ImportLibrary,
    SetFavorite,
)
from .config import (
    ANTHROPIC_API_KEY,
    CURATOR_BACKEND,
    OLLAMA_HOST,
    PROVIDERS,
    get_active_provider,
    set_active_provider,
)
from .infrastructure.ai.curator import AnthropicCurator
from .infrastructure.ai.fallback_curator import NoLlmCurator
from .infrastructure.ai.ollama_curator import OllamaCurator
from .infrastructure.persistence.repository import SqliteLibraryRepository
from .infrastructure.security.token_store import KeyringTokenStore
from .infrastructure.tidal.gateway import TidalApiGateway

log = logging.getLogger("composition")


def _ollama_reachable() -> bool:
    import requests

    try:
        return requests.get(f"{OLLAMA_HOST.rstrip('/')}/api/tags", timeout=0.5).ok
    except requests.exceptions.RequestException:
        return False


def _build_curator():
    backend = CURATOR_BACKEND
    if backend == "auto":
        if ANTHROPIC_API_KEY:
            backend = "anthropic"
        elif _ollama_reachable():
            backend = "ollama"
        else:
            backend = "none"
    chosen = {
        "anthropic": AnthropicCurator,
        "ollama": OllamaCurator,
        "none": NoLlmCurator,
    }.get(backend, NoLlmCurator)
    log.info("Discovery curator backend: %s", chosen.backend_name)
    return chosen()


@dataclass
class ProviderAdapters:
    """The adapter set for one provider. Any port may be None if unsupported."""

    auth: object
    music: object
    catalog: object
    favorites: object
    playlists: object
    recommendations: Optional[object]


def build_provider_adapters(provider: str) -> ProviderAdapters:
    if provider == "tidal":
        gw = TidalApiGateway()
        return ProviderAdapters(gw, gw, gw, gw, gw, gw)
    if provider == "spotify":
        # Imported lazily so the rest of the app works without the Spotify deps.
        from .infrastructure.lastfm.recommendation import LastfmRecommendationGateway
        from .infrastructure.spotify.gateway import SpotifyGateway

        gw = SpotifyGateway()
        rec = LastfmRecommendationGateway(gw)
        return ProviderAdapters(gw, gw, gw, gw, gw, rec)
    if provider == "qobuz":
        from .infrastructure.lastfm.recommendation import LastfmRecommendationGateway
        from .infrastructure.qobuz.gateway import QobuzGateway

        gw = QobuzGateway()
        rec = LastfmRecommendationGateway(gw)
        return ProviderAdapters(gw, gw, gw, gw, gw, rec)
    raise ValueError(f"provider not implemented yet: {provider}")


class Container:
    def __init__(self, provider: str) -> None:
        self.provider = provider
        a = build_provider_adapters(provider)
        self.auth = a.auth  # exposed for provider-specific routes (e.g. OAuth callback)
        self.repository = SqliteLibraryRepository(provider)
        self.token_store = KeyringTokenStore(provider)
        self.curator = _build_curator()
        self.curator_backend = self.curator.backend_name

        # Auth use cases (generic over any AuthGateway).
        self.connect = ConnectTidal(a.auth, self.token_store)
        self.restore_session = RestoreSession(a.auth, self.token_store)
        self.get_status = GetStatus(a.auth)
        self.logout = Logout(a.auth, self.token_store)

        # Library.
        self.import_library = ImportLibrary(a.music, self.repository)
        self.get_playlists = GetPlaylists(self.repository)
        self.get_playlist_tracks = GetPlaylistTracks(self.repository)
        self.get_favorites = GetFavorites(self.repository)
        self.manage_playlists = ManagePlaylists(a.playlists, a.music, self.repository)

        # Catalog.
        self.search_catalog = SearchCatalog(a.catalog)
        self.set_favorite = SetFavorite(a.favorites)

        # Discovery (recommendations adapter may be None for some providers).
        self.generate_recommendations = GenerateRecommendations(
            self.repository, a.recommendations, self.curator
        )
        self.save_recommendations = SaveRecommendationsToPlaylist(
            a.playlists, a.recommendations, a.music, self.repository
        )


# --- active container management (rebuilt on provider switch) ---
_active: Optional[Container] = None


def container() -> Container:
    global _active
    desired = get_active_provider()
    if _active is None or _active.provider != desired:
        log.info("Building container for provider: %s", desired)
        _active = Container(desired)
    return _active


def switch_provider(provider: str) -> None:
    global _active
    set_active_provider(provider)
    _active = None  # force rebuild
    # Restore the newly-active provider's stored session (if any).
    try:
        container().restore_session()
    except Exception as e:
        log.warning("restore after provider switch failed: %s", e)


def list_providers() -> list[dict]:
    """Each provider with active + connected (a stored session exists) flags."""
    active = get_active_provider()
    out = []
    for name in PROVIDERS:
        try:
            connected = KeyringTokenStore(name).load() is not None
        except Exception:
            connected = False
        out.append({"provider": name, "active": name == active, "connected": connected})
    return out
