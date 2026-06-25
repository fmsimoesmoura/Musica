# Phase-1 Data Schema (v0.1 — draft for iteration)

> Implements [PROJECT.md](../PROJECT.md) §8, with the v0.3 decisions baked in. Local
> SQLite now, **designed to port to the community backend unchanged**. Not yet locked —
> this is the artifact we iterate on before Phase-1 code.

## Principles

1. **Neutral identity.** Tracks are keyed by **`track_key`** = `ISRC` (or a synthesized
   key when ISRC is absent), with MusicBrainz IDs attached. Provider track ids are
   **local-only** lookups and never leave the device / never enter an export.
2. **Export-safe by construction.** Every column is tagged **E** (export-safe: neutral,
   non-personal, redistributable) or **L** (local-only: personal or provider-proprietary).
   The publishable dataset is a *view* over **E** columns only (§ Export view).
3. **Unrecoverable fields logged from day one** (⚠): propensity, arm/assignment,
   inference config, familiarity flags. Adding them later cannot recover past data.
4. **Temporal integrity.** Everything is timestamped; feature snapshots carry **no
   information after the row's `created_at`** (forward-chaining for clean splits).
5. **Identity is separable.** The `user_id`↔real-identity map lives in its own
   access-controlled store; deleting a map row de-identifies all that user's rows
   (the erasure "de-link"; PROJECT §10).

Types are SQLite-flavored (`TEXT`/`INTEGER`/`REAL`/`TIMESTAMP`/`BOOLEAN`/`JSON`).

---

## Tables

### `identity_map` — **L**, stored separately & access-controlled
The only place that links a person to their pseudonym. Never in any export; deleting a
row here is the erasure "de-link."

| col | type | notes |
|---|---|---|
| `user_id` | TEXT PK | opaque pseudonym (UUID) used everywhere else |
| `identity` | TEXT | account/email/etc. — the personal datum |
| `created_at` | TIMESTAMP | |
| `deleted_at` | TIMESTAMP NULL | set on erasure (row then purged) |

### `app_user` — pseudonymous principal
| col | type | tag | notes |
|---|---|---|---|
| `user_id` | TEXT PK | E* | pseudonym; *E only because it carries no identity, but treat as a quasi-identifier — see §10 |
| `created_at` | TIMESTAMP | E | |
| `tombstoned_at` | TIMESTAMP NULL | E | erasure tombstone — excluded from all future training/splits |

### `consent` — gate for any analysis-bound use
Invariant: **no analysis-bound collection/upload without a current valid row.**

| col | type | tag | notes |
|---|---|---|---|
| `user_id` | TEXT FK | E | |
| `consent_version` | TEXT | E | version of the information sheet agreed |
| `granted_at` | TIMESTAMP | E | |
| `publish_consent` | BOOLEAN | E | *separate* opt-in for a future public dataset release |
| `withdrawn_at` | TIMESTAMP NULL | E | opt-out |

### `model_version` — what produced a suggestion (attribution registry)
| col | type | tag | notes |
|---|---|---|---|
| `model_id` | TEXT | E | e.g. `llm`, `reranker`, `cf`, `two_tower`, `popular`, `random`, `llm_curator` |
| `model_version` | TEXT | E | semantic version / git sha of the arm |
| `family` | TEXT | E | `baseline` \| `classical` \| `llm` \| `hybrid` |
| `config_digest` | TEXT | E | hash of the full config (PK = `model_id`+`model_version`) |
| `created_at` | TIMESTAMP | E | |

### `suggestion_event` — one served candidate (the attribution record)
| col | type | tag | notes |
|---|---|---|---|
| `id` | TEXT PK | E | |
| `user_id` | TEXT FK | E* | |
| `created_at` | TIMESTAMP | E | the temporal anchor for this row |
| `surface_provider` | TEXT | L | tidal/spotify/qobuz — where it was shown (not a feature) |
| `seed_context_hash` | TEXT | E | stable hash of the seed playlists/favorites |
| `seed_context_snapshot` | JSON | L | the seed track_keys used (kept local; hash is the export key) |
| `track_key` | TEXT FK | E | **ISRC** (neutral); the candidate |
| `provider_track_id` | TEXT | L | transient lookup only; **never exported** |
| `rank` | INTEGER | E | position in the served list |
| `score` | REAL | E | the arm's score for this candidate |
| `explanation` | TEXT | E | natural-language "why" (LLM/templated) |
| `model_id` | TEXT FK | E | → `model_version` |
| `model_version` | TEXT FK | E | → `model_version` |
| ⚠ `arm` | TEXT | E | which experimental arm served it |
| ⚠ `assignment` | TEXT | E | `exploit` \| `explore` |
| ⚠ `exploration_policy_id` | TEXT | E | id of the policy (e.g. `epsilon_greedy@0.1`) |
| ⚠ `epsilon` | REAL | E | exploration rate in effect |
| ⚠ `propensity` | REAL | E | P(item shown \| policy, context) — for IPS/SNIPS (§9) |
| ⚠ `inference_config` | JSON | E | LLM determinism: model id+quant digest, temperature, top_p, seed, prompt_template_hash |

### `rating_event` — the human label
| col | type | tag | notes |
|---|---|---|---|
| `id` | TEXT PK | E | |
| `suggestion_id` | TEXT FK | E | → `suggestion_event` (carries all attribution) |
| `user_id` | TEXT FK | E* | |
| `track_key` | TEXT FK | E | denormalized for convenience |
| `rating` | INTEGER | E | **1–5** |
| `rated_at` | TIMESTAMP | E | |
| ⚠ `already_known` | BOOLEAN | E | mandatory — familiarity-bias control + discovery endpoint (§9) |
| ⚠ `already_in_library` | BOOLEAN | E | mandatory — was it already saved/added |

### `track` — neutral catalog + feature cache (open data only)
Populated from the open sources in PROJECT §8; **no provider-proprietary metadata.**

| col | type | tag | notes |
|---|---|---|---|
| `track_key` | TEXT PK | E | ISRC (or synthesized) |
| `mbid_recording` | TEXT | E | MusicBrainz recording id |
| `mbid_artist` | TEXT | E | MusicBrainz artist id |
| `title` | TEXT | E | from MusicBrainz (CC0) |
| `artist_name` | TEXT | E | from MusicBrainz (CC0) |
| `release_date` | TEXT | E | from MusicBrainz |
| `mb_tags` | JSON | E | MusicBrainz folksonomy genre tags (CC0) |
| `ab_features` | JSON | E | AcousticBrainz descriptors (CC0), by MBID |
| `lastfm_tags` | JSON | **L** | local-only model input; **excluded from export** (Last.fm ToS) |
| `feature_snapshot_at` | TIMESTAMP | E | when features were fetched (≤ using-row's `created_at`) |

---

## Export view (the shareable dataset)

`SELECT` of **E**-tagged columns only, joining `rating_event` → `suggestion_event` →
`track`, **excluding** `provider_track_id`, `seed_context_snapshot`, `lastfm_tags`,
`surface_provider`, and the entire `identity_map`. Rows for `tombstoned_at IS NOT NULL`
users are dropped. The result is *"`user_id`, `track_key`, `rating`, attribution,
CC0 features"* — a MovieLens-style matrix, gated on `publish_consent` for any public
release.

> Note: even export-safe, `user_id` is a **quasi-identifier** in combination with
> ratings; published releases get the additional de-identification in PROJECT §10.

---

## Open items (for the next iteration)

- **[OPEN]** synthesized `track_key` rule when ISRC is missing (e.g. hash of
  MBID / normalized artist+title).
- **[OPEN]** store `seed_context_snapshot` inline vs. a separate `seed_track` join table.
- **[OPEN]** exact `ab_features` / `mb_tags` field subset to retain.
- **[OPEN]** retention window + the physical split of `identity_map` (separate DB/file
  vs. OS keychain).
- Confirm consent-record content with the chosen **ethics/IRB** path (PROJECT §10).
