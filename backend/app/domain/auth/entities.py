"""Auth domain entities — pure data."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


@dataclass
class OAuthTokens:
    token_type: str
    access_token: str
    refresh_token: Optional[str] = None
    expiry_time: Optional[datetime] = None


@dataclass
class LinkLogin:
    """The device/link login challenge shown to the user."""

    login_id: str
    verification_uri: str
    user_code: str
    expires_in: int


class LoginStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


@dataclass
class LoginResult:
    status: LoginStatus
    connected: bool = False
    user_name: Optional[str] = None


@dataclass
class ConnectionStatus:
    connected: bool
    user_name: Optional[str] = None
