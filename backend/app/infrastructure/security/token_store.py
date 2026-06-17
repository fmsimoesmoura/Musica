"""KeyringTokenStore — implements the TokenStore port via the OS keychain.

Falls back to a 0600 file if no keyring backend is available (e.g. headless).
Translates between the OAuthTokens domain entity and a JSON payload.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from ...config import KEYRING_SERVICE, KEYRING_USER, app_data_dir
from ...domain.auth.entities import OAuthTokens

_FALLBACK_PATH = app_data_dir() / "session.json"


class KeyringTokenStore:
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
            keyring.set_password(KEYRING_SERVICE, KEYRING_USER, payload)
            return
        except KeyringError:
            pass
        _FALLBACK_PATH.write_text(payload)
        os.chmod(_FALLBACK_PATH, 0o600)

    def load(self) -> Optional[OAuthTokens]:
        payload: Optional[str] = None
        try:
            payload = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
        except KeyringError:
            payload = None
        if payload is None and _FALLBACK_PATH.exists():
            payload = _FALLBACK_PATH.read_text()
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
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
        except (KeyringError, PasswordDeleteError):
            pass
        if _FALLBACK_PATH.exists():
            _FALLBACK_PATH.unlink()
