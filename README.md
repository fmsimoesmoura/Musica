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
├── domain/{auth,library,catalog,discovery}/  entities + port interfaces (pure Python)
├── application/{auth,library,catalog,discovery}/ use cases (ConnectTidal, ImportLibrary,
│                                   SearchCatalog, SetFavorite, GenerateRecommendations, …)
├── infrastructure/
│   ├── tidal/gateway.py        the only file that imports tidalapi
│   ├── ai/curator.py           the only file that imports the Anthropic SDK
│   ├── persistence/            SQLModel tables, engine, repository
│   └── security/token_store.py OS keychain token storage
├── interface/http/routers.py   FastAPI routes (thin)
├── composition.py              DI root — wires adapters into use cases
└── main.py                     FastAPI app + entrypoint

desktop/
├── src/                        React UI (ConnectPanel, LibraryView, SearchView, DiscoverView)
└── src-tauri/                  Rust shell (spawns + supervises the sidecar)
```

## Features — what each one does

### Connect (OAuth)
Logs you into Tidal using the **device/link flow**: the app asks Tidal for a code,
opens `link.tidal.com/XXXXX` in your browser, and polls until you approve. On
success the OAuth tokens (`access`/`refresh`/expiry) are saved to the **macOS
keychain**. On every launch the app restores that session automatically and
refreshes the access token if it has expired — so you only log in once.
*Use case:* `ConnectTidal`, `RestoreSession`. *Log out* clears the keychain entry.

### Import library
Pulls your **owned music** from Tidal into a local SQLite DB so the UI is instant
and works offline-ish. Specifically:
- **All your playlists** + each playlist's **ordered track list** (paginated, 100 at a time).
- **Favorites**: favorite tracks, artists, and albums.

It's a full **snapshot** written in one transaction, keyed by Tidal id, so
re-running it ("Re-sync") **updates in place — never duplicates**. Returns counts
(playlists / playlist-tracks / fav tracks / artists / albums).
*Use case:* `ImportLibrary`. *Does NOT* import other users' playlists or your play history.

### Browse library
Reads back the imported data (no Tidal call): list playlists with track counts,
open a playlist to see its tracks in order, and tabs for favorite **artists** and
**tracks**. *Use cases:* `GetPlaylists`, `GetPlaylistTracks`, `GetFavorites`.

### Search catalog
Searches **all of Tidal's catalog** (not just your library) via Tidal's search.
Returns the **top ~30 matches per category** for **artists, albums, and tracks**,
relevance-ranked. Results reflect what's available in your account's region.
It is query-based (you type something); it does not yet paginate or include
videos/public playlists. *Use case:* `SearchCatalog`.

### Favorite / unfavorite
From any search result you can ♥ an artist, album, or track. This **writes
directly to your Tidal favorites** (add or remove). The UI toggles optimistically;
the local DB reflects the change on the next **Re-sync**. *Use case:* `SetFavorite`.

### Discover (hybrid AI)
Finds **new artists you don't already have** that fit your taste:
1. **Seed** from your favorite artists (up to 12).
2. **Candidates** from Tidal's *similar artists* for each seed, scored by how many
   seeds they relate to (artists already in your library are filtered out).
3. **Curate** — Claude (`claude-opus-4-8` by default) ranks the candidates and writes
   a one-sentence reason each fits your taste, grounded in your actual seed artists.

Each recommendation can be ♥-favorited straight to Tidal.
*Use case:* `GenerateRecommendations`; candidate adapter `TidalApiGateway.similar_artists`.

**The curation backend is pluggable** (`CURATOR_BACKEND`, default `auto`) — the
`Curator` port means each is just an adapter:

| `CURATOR_BACKEND` | Adapter | Needs | Notes |
|---|---|---|---|
| `anthropic` | `AnthropicCurator` | `ANTHROPIC_API_KEY` | Best quality; billed at API rates (separate from a Claude Max subscription) |
| `ollama` | `OllamaCurator` | local [Ollama](https://ollama.com) + a model | Free, private, offline; lower nuance |
| `none` | `NoLlmCurator` | nothing | Ranks by Tidal similarity score; templated reasons; zero setup |
| `auto` (default) | — | — | Claude if a key is set → else Ollama if running → else `none` |

So Discover works out of the box with no keys (`none`), upgrades to a free local
LLM if Ollama is running, and to Claude if a key is present. See issue #5 for the
analysis (incl. a spike on using a Claude Max subscription via the Agent SDK).

### Playlist editing & save-to-playlist
Create, rename, and delete playlists, and add/remove tracks — all **written
directly to Tidal**, with just the affected playlist re-fetched into the local DB
so the UI updates without a full re-sync. From **Discover**, "Save as playlist"
turns the current picks into a new Tidal playlist seeded with each artist's top
track. *Use cases:* `ManagePlaylists`, `SaveRecommendationsToPlaylist`; adapter
`TidalApiGateway` (create/add/remove/edit/delete via `UserPlaylist`).

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

| Method | Path | Purpose | Behavior notes |
|---|---|---|---|
| GET | `/health` | readiness check | returns `{ok:true}`; used by the shell/UI to wait for the sidecar |
| POST | `/auth/start` | begin device/link login | returns `{login_id, verification_uri, user_code, expires_in}` |
| GET | `/auth/poll?login_id=` | poll login status | `status`: `pending`/`authorized`/`expired`/`unknown`; persists tokens on success |
| GET | `/auth/status` | connection state | `{connected, user_name}` |
| POST | `/auth/logout` | clear session | wipes keychain tokens, resets the Tidal session |
| POST | `/library/import` | import playlists + favorites | idempotent upsert; returns counts |
| GET | `/playlists` | list imported playlists | local read |
| GET | `/playlists/{id}/tracks` | tracks in a playlist | local read, ordered |
| GET | `/favorites?type=tracks\|artists\|albums` | favorites | local read |
| GET | `/search?q=&include=artists,albums,tracks` | catalog search | live Tidal call; top ~30 per type; needs connection |
| POST | `/favorites/{type}/{id}` | add a favorite | writes to Tidal; `type` ∈ track/artist/album |
| DELETE | `/favorites/{type}/{id}` | remove a favorite | writes to Tidal |
| POST | `/discover?limit=` | AI-curated new-artist recommendations | Tidal similar-artists + curator backend |
| POST | `/discover/save` | save discovery picks as a Tidal playlist | `{name, artist_ids, tracks_per_artist}` |
| POST | `/playlists` | create a playlist | `{title, description?}` → `{playlist_id}` |
| PATCH | `/playlists/{id}` | rename/edit a playlist | `{title?, description?}` |
| DELETE | `/playlists/{id}` | delete a playlist | writes to Tidal |
| POST | `/playlists/{id}/tracks` | add tracks | `{track_ids: [int]}` |
| DELETE | `/playlists/{id}/tracks/{track_id}` | remove a track | writes to Tidal |

All endpoints except `/health` and the auth routes require an active Tidal
connection (return `401` otherwise).

Local data lives in `~/Library/Application Support/tidal-manager/library.db`;
OAuth tokens are stored in the macOS keychain.

## Roadmap

- **M1 — Auth + library import** ✅ connect to Tidal, import playlists & favorites, browse them.
- **M2 — Search & favorite** ✅ full-catalog search (tracks/albums/artists), ♥ add/remove favorites.
- **M3 — Hybrid discovery** ✅ seed from your favorites → Tidal similar-artists for
  candidates → Claude ranks & explains fit → ♥ picks to your favorites.
- **M4 — Playlist editing + packaging** — editing ✅ (create/rename/delete, add/remove
  tracks, save discovery picks to a playlist); packaging ⏳ (PyInstaller sidecar +
  Tauri `externalBin` + signed `.app`/`.dmg`).

Progress is tracked in GitHub issues (#4 is the roadmap).
