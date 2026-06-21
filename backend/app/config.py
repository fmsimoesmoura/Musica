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

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
# Claude model used for AI-curated discovery (M3). Override via env if desired.
DISCOVERY_MODEL = os.environ.get("DISCOVERY_MODEL", "claude-opus-4-8")

# Which backend curates discovery recommendations:
#   auto      -> anthropic if a key is set, else ollama if reachable, else none
#   anthropic -> Claude via the Anthropic API (needs ANTHROPIC_API_KEY)
#   ollama    -> a local LLM via Ollama (free, offline)
#   none      -> no LLM; rank by Tidal similarity score with templated reasons
CURATOR_BACKEND = os.environ.get("CURATOR_BACKEND", "auto").lower()
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

# --- Spotify connector (official Web API; Authorization Code + PKCE) ---
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_REDIRECT_URI = os.environ.get(
    "SPOTIFY_REDIRECT_URI", f"http://127.0.0.1:{DEFAULT_PORT}/auth/spotify/callback"
)
# Scopes for library read + playlist/favorite write.
SPOTIFY_SCOPES = (
    "user-library-read user-library-modify "
    "playlist-read-private playlist-modify-private playlist-modify-public "
    "user-follow-read user-follow-modify"
)

# --- Last.fm (free) — similar-artists source for Spotify discovery ---
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY")
