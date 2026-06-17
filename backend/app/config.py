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
