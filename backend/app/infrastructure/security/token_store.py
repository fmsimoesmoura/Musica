"""KeyringTokenStore — implements the TokenStore port via the OS keychain,
namespaced per provider. Falls back to a 0600 file if no keyring backend is
available (e.g. headless). Translates between OAuthTokens and a JSON payload.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from ...config import KEYRING_SERVICE, app_data_dir, keyring_user_for
from ...domain.auth.entities import OAuthTokens


class KeyringTokenStore:
    def __init__(self, provider: str):
        self._provider = provider
        self._user = keyring_user_for(provider)
        self._fallback = app_data_dir() / f"session-{provider}.json"
        # Pre-namespacing key (Tidal-only), for one-time back-compat on load.
        self._legacy_user = "oauth-session" if provider == "tidal" else None
        self._legacy_fallback = app_data_dir() / "session.json"

    def save(self, tokens: OAuthTokens) -> None:
        payload = json.dumps(
            {
                "token_type": tokens.token_type,
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "expiry_time": tokens.expiry_time.isoformat() if tokens.expiry_time else None,
            }
        )
        try:
            keyring.set_password(KEYRING_SERVICE, self._user, payload)
            return
        except KeyringError:
            pass
        self._fallback.write_text(payload)
        os.chmod(self._fallback, 0o600)

    def load(self) -> Optional[OAuthTokens]:
        payload: Optional[str] = None
        try:
            payload = keyring.get_password(KEYRING_SERVICE, self._user)
        except KeyringError:
            payload = None
        if payload is None and self._fallback.exists():
            payload = self._fallback.read_text()
        # Back-compat: migrate the pre-namespacing Tidal session if present.
        if payload is None and self._legacy_user:
            try:
                payload = keyring.get_password(KEYRING_SERVICE, self._legacy_user)
            except KeyringError:
                payload = None
            if payload is None and self._legacy_fallback.exists():
                payload = self._legacy_fallback.read_text()
        if not payload:
            return None
        data = json.loads(payload)
        expiry = data.get("expiry_time")
        return OAuthTokens(
            token_type=data["token_type"],
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expiry_time=datetime.fromisoformat(expiry) if expiry else None,
        )

    def clear(self) -> None:
        try:
            keyring.delete_password(KEYRING_SERVICE, self._user)
        except (KeyringError, PasswordDeleteError):
            pass
        if self._fallback.exists():
            self._fallback.unlink()
