# Tidal Manager

A personal desktop app to manage your Tidal playlists, search the catalog, and
discover new artists that fit your taste (Tidal radio + AI curation).

> **Note on the Tidal API.** This app uses [`tidalapi`](https://github.com/EbbLabs/python-tidal),
> the actively maintained *unofficial* Python library, because it supports full
> playlist management, favorites, search, and track/artist radio — capabilities
> Tidal's official Developer API does not fully expose. It rides Tidal's internal
> API, so it is technically outside Tidal's ToS and can break when Tidal changes
> things. Fine for personal use; the dependency is isolated to a single adapter
> (`backend/app/infrastructure/tidal/gateway.py`) so it can be swapped.

## Architecture

Pragmatic **Clean Architecture** — dependencies point inward, third-party SDKs
live only in `infrastructure`.

```
interface  →  application  →  domain  ←  infrastructure
(FastAPI)      (use cases)    (entities,     (tidalapi, sqlite,
                              ports)          keyring, anthropic)
```

Two processes:

- **`backend/`** — Python sidecar (FastAPI). Owns *all* Tidal + AI logic. Exposes
  a small local HTTP API on `127.0.0.1:8765`.
- **`desktop/`** — Tauri 2 shell (Rust) + React/TS UI. In dev the Rust shell
  spawns the Python sidecar and the UI talks to it over localhost.

```
backend/app/
├── domain/{library,auth}/      entities + port interfaces (pure Python)
├── application/{library,auth}/ use cases (ImportLibrary, ConnectTidal, …)
├── infrastructure/
│   ├── tidal/gateway.py        the only file that imports tidalapi
│   ├── persistence/            SQLModel tables, engine, repository
│   └── security/token_store.py OS keychain token storage
├── interface/http/routers.py   FastAPI routes (thin)
├── composition.py              DI root — wires adapters into use cases
└── main.py                     FastAPI app + entrypoint

desktop/
├── src/                        React UI (ConnectPanel, LibraryView, api client)
└── src-tauri/                  Rust shell (spawns + supervises the sidecar)
```

## Running (dev)

Prereqs: Python 3.12 (`uv`), Node, Rust.

```bash
# 1. Backend deps
cd backend && uv venv --python 3.12 && uv pip install -e .

# 2. Desktop deps
cd ../desktop && npm install

# 3. Run the whole app (Rust shell auto-spawns the Python sidecar)
npm run tauri dev
```

To run the backend alone (e.g. for curl testing):

```bash
cd backend && .venv/bin/python -m app.main --port 8765
```

### HTTP API (sidecar)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | readiness check |
| POST | `/auth/start` | begin device/link login → returns `link.tidal.com` URL |
| GET | `/auth/poll?login_id=` | poll login status |
| GET | `/auth/status` | `{connected, user_name}` |
| POST | `/auth/logout` | clear session |
| POST | `/library/import` | import playlists + favorites into SQLite |
| GET | `/playlists` | list imported playlists |
| GET | `/playlists/{id}/tracks` | tracks in a playlist |
| GET | `/favorites?type=tracks\|artists\|albums` | favorites |

Local data lives in `~/Library/Application Support/tidal-manager/library.db`;
OAuth tokens are stored in the macOS keychain.

## Roadmap

- **M1 — Auth + library import** ✅ connect to Tidal, import playlists & favorites, browse them.
- **M2 — Search** catalog search (tracks/albums/artists), add to favorites.
- **M3 — Hybrid discovery** seed from your favorites → Tidal radio/similar-artists
  for candidates → Claude ranks & explains fit → save picks to a playlist.
- **M4 — Playlist editing + packaging** create/edit playlists; PyInstaller sidecar
  + signed `.app`/`.dmg`.
