"""Auth use cases — orchestrate the AuthGateway and TokenStore.

These contain the *coordination* logic (e.g. persist tokens after a successful
login or refresh) while delegating service-specific work to the gateway.
"""
from __future__ import annotations

import logging

from ...domain.auth.entities import (
    ConnectionStatus,
    LinkLogin,
    LoginResult,
    LoginStatus,
)
from ...domain.auth.ports import AuthGateway, TokenStore

log = logging.getLogger("app.auth")


class ConnectTidal:
    def __init__(self, gateway: AuthGateway, store: TokenStore):
        self._gateway = gateway
        self._store = store

    def start(self) -> LinkLogin:
        return self._gateway.start_login()

    def poll(self, login_id: str) -> LoginResult:
        result = self._gateway.poll_login(login_id)
        if result.status is LoginStatus.AUTHORIZED:
            tokens = self._gateway.current_tokens()
            if tokens:
                self._store.save(tokens)
        return result


class RestoreSession:
    def __init__(self, gateway: AuthGateway, store: TokenStore):
        self._gateway = gateway
        self._store = store

    def __call__(self) -> bool:
        tokens = self._store.load()
        if not tokens:
            return False
        if not self._gateway.restore(tokens):
            return False
        # The gateway may have refreshed the access token; persist the latest.
        refreshed = self._gateway.current_tokens()
        if refreshed:
            self._store.save(refreshed)
        return True


class GetStatus:
    def __init__(self, gateway: AuthGateway):
        self._gateway = gateway

    def __call__(self) -> ConnectionStatus:
        return self._gateway.status()


class Logout:
    def __init__(self, gateway: AuthGateway, store: TokenStore):
        self._gateway = gateway
        self._store = store

    def __call__(self) -> None:
        self._gateway.disconnect()
        self._store.clear()
