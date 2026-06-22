"""App-wide configuration and filesystem locations."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "tidal-manager"

# Supported music-service providers. Tidal is the default/active provider.
PROVIDERS = ("tidal", "spotify", "qobuz")
DEFAULT_PROVIDER = "tidal"


def app_data_dir() -> Path:
    """Per-user writable directory for the local DB and any cached state.

    macOS: ~/Library/Application Support/tidal-manager
    Linux: $XDG_DATA_HOME/tidal-manager or ~/.local/share/tidal-manager
    Windows: %APPDATA%/tidal-manager
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


DEFAULT_PORT = int(os.environ.get("TIDAL_MANAGER_PORT", "8765"))

# One SQLite file per provider (keeps each service's library isolated).
def db_path_for(provider: str) -> Path:
    return app_data_dir() / f"library-{provider}.db"


# Active-provider setting, persisted in a small JSON file.
_SETTINGS_PATH = app_data_dir() / "settings.json"


def get_active_provider() -> str:
    try:
        value = json.loads(_SETTINGS_PATH.read_text()).get("active_provider")
        if value in PROVIDERS:
            return value
    except (OSError, ValueError):
        pass
    return DEFAULT_PROVIDER


def set_active_provider(provider: str) -> None:
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider: {provider}")
    _SETTINGS_PATH.write_text(json.dumps({"active_provider": provider}))


# Keychain identifiers for token persistence (namespaced per provider).
KEYRING_SERVICE = "tidal-manager"


def keyring_user_for(provider: str) -> str:
    return f"oauth-session-{provider}"

# --- Runtime-editable settings (Settings screen) -------------------------
# Keys live in a 0600 config.json in the app data dir so the *installed* app can
# be configured without a .env or rebuild. Resolution order: config.json → env.
_CONFIG_PATH = app_data_dir() / "config.json"

# Keys the Settings screen manages. `secret` ones are never echoed back to the UI.
SETTING_KEYS = {
    "SPOTIFY_CLIENT_ID": {"secret": False},
    "LASTFM_API_KEY": {"secret": True},
    "QOBUZ_APP_ID": {"secret": False},
    "ANTHROPIC_API_KEY": {"secret": True},
    "CURATOR_BACKEND": {"secret": False},
    "OLLAMA_HOST": {"secret": False},
    "OLLAMA_MODEL": {"secret": False},
    "DISCOVERY_MODEL": {"secret": False},
    "SPOTIFY_REDIRECT_URI": {"secret": False},
}


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text())
    except (OSError, ValueError):
        return {}


def get_setting(key: str) -> str | None:
    """config.json value (if non-empty) else environment variable else None."""
    val = _load_config().get(key)
    if val:
        return val
    env = os.environ.get(key)
    return env if env else None


def update_settings(values: dict) -> None:
    cfg = _load_config()
    for k, v in values.items():
        if k not in SETTING_KEYS:
            continue
        if v is None or v == "":
            cfg.pop(k, None)  # clearing falls back to env/default
        else:
            cfg[k] = v
    _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    os.chmod(_CONFIG_PATH, 0o600)


def settings_view() -> dict:
    """For the UI: non-secret values verbatim; secrets only as configured?-booleans."""
    out = {}
    for key, meta in SETTING_KEYS.items():
        if meta["secret"]:
            out[key] = {"secret": True, "configured": get_setting(key) is not None}
        else:
            out[key] = {"secret": False, "value": get_setting(key) or ""}
    return out


# Getters used across the app (always current).
def anthropic_api_key() -> str | None:
    return get_setting("ANTHROPIC_API_KEY")


def discovery_model() -> str:
    return get_setting("DISCOVERY_MODEL") or "claude-opus-4-8"


def curator_backend() -> str:
    return (get_setting("CURATOR_BACKEND") or "auto").lower()


def ollama_host() -> str:
    return get_setting("OLLAMA_HOST") or "http://localhost:11434"


def ollama_model() -> str:
    return get_setting("OLLAMA_MODEL") or "llama3.1:8b"


def spotify_client_id() -> str | None:
    return get_setting("SPOTIFY_CLIENT_ID")


def spotify_redirect_uri() -> str:
    return get_setting("SPOTIFY_REDIRECT_URI") or f"http://127.0.0.1:{DEFAULT_PORT}/auth/spotify/callback"


def lastfm_api_key() -> str | None:
    return get_setting("LASTFM_API_KEY")


def qobuz_app_id() -> str | None:
    return get_setting("QOBUZ_APP_ID")


# Static (not user-editable): Spotify OAuth scopes.
SPOTIFY_SCOPES = (
    "user-library-read user-library-modify "
    "playlist-read-private playlist-modify-private playlist-modify-public "
    "user-follow-read user-follow-modify"
)
