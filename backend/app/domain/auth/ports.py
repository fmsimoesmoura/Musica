"""Auth ports — interfaces the application layer depends on.

Infrastructure adapters implement these. Defined with Protocol so adapters need
no explicit inheritance (structural typing).
"""
from __future__ import annotations

from typing import Optional, Protocol

from .entities import ConnectionStatus, LinkLogin, LoginResult, OAuthTokens


class AuthGateway(Protocol):
    """The Tidal-side authentication boundary."""

    def start_login(self) -> LinkLogin:
        """Begin a device/link login; returns the challenge to show the user."""

    def poll_login(self, login_id: str) -> LoginResult:
        """Check on an in-flight login."""

    def status(self) -> ConnectionStatus:
        ...

    def restore(self, tokens: OAuthTokens) -> bool:
        """Reload a persisted session, refreshing if expired. Returns connected?"""

    def current_tokens(self) -> Optional[OAuthTokens]:
        """The live session's tokens, for persistence after login/refresh."""

    def disconnect(self) -> None:
        ...


class TokenStore(Protocol):
    """Secure persistence of the OAuth session."""

    def save(self, tokens: OAuthTokens) -> None:
        ...

    def load(self) -> Optional[OAuthTokens]:
        ...

    def clear(self) -> None:
        ...
