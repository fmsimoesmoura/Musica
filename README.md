# Tidal Manager

**v0.4.0 · macOS + Windows · Tidal + Spotify + Qobuz**

A personal desktop app to manage your music — across **Tidal**, **Spotify**, and
**Qobuz** — search each catalog, and discover new artists that fit your taste
(streaming "similar artists" + AI curation). Built with a Python sidecar + a
Tauri/React desktop shell; ships for **macOS (Apple Silicon)** and **Windows (x64)**.

Switch services with the provider toggle in the title bar; each keeps its own
imported library and login.

> **Note on the Tidal API.** This app uses [`tidalapi`](https://github.com/EbbLabs/python-tidal),
> the actively maintained *unofficial* Python library, because it supports full
> playlist management, favorites, search, and track/artist radio — capabilities
> Tidal's official Developer API does not fully expose. It rides Tidal's internal
> API, so it is technically outside Tidal's ToS and can break when Tidal changes
> things. Fine for personal use; the dependency is isolated to a single adapter
> (`backend/app/infrastructure/tidal/gateway.py`) so it can be swapped.

## Connectors

Each music service is a set of adapters behind shared ports
(`AuthGateway`, `CatalogGateway`, `FavoritesGateway`, `PlaylistWriter`,
`RecommendationGateway`). The active provider is chosen in the title bar; libraries
are isolated per provider (`library-<provider>.db`) with per-provider logins.

| Provider | Auth | Import | Search | Favorites | Playlists | Discovery |
|---|---|---|---|---|---|---|
| **Tidal** | device/link | ✅ | ✅ | ✅ | ✅ | Tidal similar-artists |
| **Spotify** | OAuth PKCE | ✅ | ✅ | ✅ | ✅ | **Last.fm** similar-artists¹ |
| **Qobuz** | email/password | ✅ | ✅ | ✅ | ✅ | **Last.fm** similar-artists¹ |

¹ Spotify deprecated its `related-artists`/`recommendations` endpoints for new
apps, so Spotify discovery uses Last.fm's free `artist.getSimilar` for candidates,
then the same curator (Ollama/Claude/none) ranks them. Spotify's own
artist-top-tracks (used by "save discovery as playlist") still works.

### Spotify setup (one-time)

1. Create an app at the [Spotify developer dashboard](https://developer.spotify.com/dashboard)
   (no client secret needed — the app uses PKCE).
2. Add this exact **redirect URI** to the app:
   `http://127.0.0.1:8765/auth/spotify/callback`
3. Put the app's **Client ID** and a free [Last.fm API key](https://www.last.fm/api/account/create)
   in `backend/.env`:
   ```
   SPOTIFY_CLIENT_ID=your_client_id
   LASTFM_API_KEY=your_lastfm_key
   ```
4. In the app, switch the provider toggle to **Spotify** → **Connect Spotify** →
   approve in the browser. (New Spotify apps are "development mode": the owner needs
   Premium and ~25 users max — fine for personal use.)

### Qobuz setup (one-time)

Qobuz has no official API; this uses the same reverse-engineered API as the web
player, which needs an **app_id** (and your account login).

1. Find the `app_id`: open [play.qobuz.com](https://play.qobuz.com) → DevTools →
   search the JS bundle for `app_id` (or take it from a project like `qobuz-dl`),
   and put it in `backend/.env`:
   ```
   QOBUZ_APP_ID=your_app_id
   LASTFM_API_KEY=your_lastfm_key   # for discovery (shared with Spotify)
   ```
2. In the app, switch to **Qobuz** and enter your Qobuz **email + password**
   (sent once to Qobuz for a long-lived token, then stored in the OS credential
   store — never written to disk in plaintext).

> Like the Tidal connector, this rides an undocumented API and is ToS-gray —
> fine for personal use, may break if Qobuz changes things.

## Download & install

Installers are built by GitHub Actions (see [Building](#building-installers)).

- **Best:** the latest GitHub **[Release](../../releases/latest)** — installers are
  attached directly (no login, permanent). Published automatically when a `v*` tag
  is pushed.
- **Untagged build:** GitHub → **Actions** → latest **build** run → **Artifacts**
  (`tidal-manager-macos`, `tidal-manager-windows`). These need a GitHub login,
  download as a `.zip` (unzip to get the installer), and expire after ~90 days.

> These are **unsigned** personal builds, so each OS shows a one-time "unverified
> developer" warning — steps below. Signing/notarization is optional and needs a
> paid developer certificate.

### macOS (Apple Silicon)

1. Download & unzip `tidal-manager-macos`, giving `Tidal Manager_<version>_aarch64.dmg`.
2. Open the `.dmg` and drag **Tidal Manager** into **Applications**.
3. First launch (Gatekeeper): **right-click the app → Open → Open**.
   (Or once: `xattr -dr com.apple.quarantine "/Applications/Tidal Manager.app"`.)
4. macOS asks to allow keychain access (enter your **Mac login password**) → click
   **Always Allow**. That's where your Tidal tokens are stored.
5. Click **Connect Tidal** → approve in the browser → **Import library**.

*Intel Macs:* no prebuilt binary — [build from source](#building-installers) on an Intel Mac.

### Windows (x64)

1. Download & unzip `tidal-manager-windows`, giving an installer:
   `Tidal Manager_<version>_x64-setup.exe` (recommended) or `Tidal Manager_<version>_x64_en-US.msi`.
2. Run it. SmartScreen may warn (unsigned) → **More info → Run anyway**.
3. If prompted, allow the **WebView2 runtime** to install (Tauri handles it; it's
   already present on Windows 11).
4. Launch **Tidal Manager** from the Start menu → **Connect Tidal** → approve in the
   browser → **Import library**.

*Tokens* are stored in the **Windows Credential Manager** (no extra prompt).

### Optional on both: free local AI discovery

Discover works with **zero setup** (ranks by Tidal similarity). For AI-written
"why it fits" reasons for free, install [Ollama](https://ollama.com), pull a model,
and keep it running — the app auto-detects it:

```bash
ollama pull llama3.1:8b   # then keep `ollama serve` running (brew services start ollama on macOS)
```

(Or set `ANTHROPIC_API_KEY` to use Claude instead — see [Discover](#discover-hybrid-ai).)

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
success the OAuth tokens (`access`/`refresh`/expiry) are saved to the **OS
credential store** (macOS Keychain / Windows Credential Manager), via `keyring`.
On every launch the app restores that session automatically and refreshes the
access token if it has expired — so you only log in once.
*Use case:* `ConnectTidal`, `RestoreSession`. *Log out* clears the stored tokens.

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

## Building installers

The same two commands build a native installer on **whatever OS you run them on**
(Python 3.12/`uv`, Node, Rust + platform toolchain required):

```bash
# 1. Bundle the Python sidecar into a single binary (PyInstaller),
#    named with the host target triple, into src-tauri/binaries/.
cd backend && uv pip install --python .venv/bin/python pyinstaller && ./build_sidecar.sh

# 2. Build the desktop app — embeds the sidecar via Tauri externalBin.
cd ../desktop && npm run tauri build
```

Outputs:
- **macOS** → `src-tauri/target/release/bundle/dmg/Tidal Manager_<version>_aarch64.dmg` (+ `.app`)
- **Windows** → `…/bundle/nsis/Tidal Manager_<version>_x64-setup.exe` and `…/bundle/msi/Tidal Manager_<version>_x64_en-US.msi`

In **release** the Rust shell launches the bundled sidecar (`tidal-backend` /
`tidal-backend.exe`, placed next to the app executable); in **dev** it launches the
venv Python — so `npm run tauri dev` needs no PyInstaller build.

### Cross-platform via CI (no second machine needed)

You **can't** cross-build a Windows app from macOS (or vice-versa) — PyInstaller and
Tauri's bundler/WebView2/MSVC toolchain are per-OS. So both installers are produced
by GitHub Actions (`.github/workflows/release.yml`) on `windows-latest` +
`macos-latest` runners:

- **Run it:** GitHub → **Actions** → *build* → **Run workflow** (artifacts only), or
  push a `v*` tag — e.g. `git tag v0.2.0 && git push origin v0.2.0` — which builds
  **and publishes a GitHub Release** with the `.dmg`/`.msi`/`.exe` attached.
- **Download:** the [Release](../../releases/latest) (tagged) or the run's artifacts
  (`tidal-manager-windows`, `tidal-manager-macos`).

### Signing (optional)

Builds are unsigned, hence the one-time OS warnings in
[Download & install](#download--install). To remove them you need a paid cert:
**macOS** an Apple Developer ID (sign + notarize); **Windows** an Authenticode
code-signing certificate.

### HTTP API (sidecar)

| Method | Path | Purpose | Behavior notes |
|---|---|---|---|
| GET | `/health` | readiness check | returns `{ok:true}`; used by the shell/UI to wait for the sidecar |
| GET | `/providers` | list providers | `[{provider, active, connected}]` |
| POST | `/providers/active` | switch active provider | `{provider}`; restores that provider's session |
| GET | `/auth/spotify/callback` | Spotify OAuth redirect target | exchanges the code; closes the loop |
| POST | `/auth/credentials` | email/password login (Qobuz) | `{username, password}` → stores token |
| POST | `/auth/start` | begin device/link login | returns `{login_id, verification_uri, user_code, expires_in}` |
| GET | `/auth/poll?login_id=` | poll login status | `status`: `pending`/`authorized`/`expired`/`unknown`; persists tokens on success |
| GET | `/auth/status` | connection state | `{connected, user_name}` |
| POST | `/auth/logout` | clear session | wipes stored tokens, resets the Tidal session |
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

Local data (SQLite `library.db`) lives in the per-user app dir — macOS
`~/Library/Application Support/tidal-manager/`, Windows `%APPDATA%\tidal-manager\`.
OAuth tokens are stored in the OS credential store (macOS Keychain / Windows
Credential Manager), falling back to a `0600` `session.json` in that dir if no
keyring backend is available.

## Roadmap

- **M1 — Auth + library import** ✅ connect to Tidal, import playlists & favorites, browse them.
- **M2 — Search & favorite** ✅ full-catalog search (tracks/albums/artists), ♥ add/remove favorites.
- **M3 — Hybrid discovery** ✅ seed from your favorites → Tidal similar-artists for
  candidates → Claude ranks & explains fit → ♥ picks to your favorites.
- **M4 — Playlist editing + packaging** ✅ editing (create/rename/delete, add/remove
  tracks, save discovery picks to a playlist) + packaging (PyInstaller sidecar via
  Tauri `externalBin`).
- **Cross-platform (v0.2.0)** ✅ macOS `.dmg` + Windows `.msi`/`.exe`, built on CI.
  Code-signing/notarization remains optional (needs paid certs).
- **Connectors (v0.3.0)** ✅ multi-provider foundation + **Spotify** (OAuth PKCE,
  import/search/favorites/playlists, Last.fm-powered discovery).
- **Qobuz connector (v0.4.0)** ✅ email/password login, import/search/favorites/
  playlists, Last.fm-powered discovery.

Progress is tracked in GitHub issues (#4 is the roadmap).
