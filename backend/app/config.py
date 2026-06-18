"""App-wide configuration and filesystem locations."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "tidal-manager"


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


DB_PATH = app_data_dir() / "library.db"
DEFAULT_PORT = int(os.environ.get("TIDAL_MANAGER_PORT", "8765"))

# Keychain identifiers for token persistence.
KEYRING_SERVICE = "tidal-manager"
KEYRING_USER = "oauth-session"

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
