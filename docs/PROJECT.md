# Music Manager — Project Definition

> **Status:** v0.1 — living draft. This document is the subject of our design
> iterations; we tune it before writing any Goal-2 code. Decisions marked
> **[OPEN]** are still being settled.

---

## 1. Purpose

This repository pursues **two goals**:

- **G1 — The application (built / evolving).** A desktop app, *Music Manager*, that
  lets users organize their library and playlists across **Tidal, Spotify, Qobuz**,
  search catalogs, and discover new artists. (See the [README](../README.md) /
  [User Guide](USER_GUIDE.md).)

- **G2 — The research subject (this project).** Use the app to build a
  **community-labeled music-recommendation loop**: the system suggests new
  music/artists from a user's playlists; users **rate each suggestion 1–5**; we
  collect that feedback and use it to **select and train** a recommender that
  measurably improves over time.

G1 is the vehicle; **G2 is the research.**

## 2. The core loop

```
 user's playlists / taste
          │
          ▼
   model suggests tracks ─────────►  user rates each 1–5
          ▲                                   │
          │                                   ▼
  select / train model  ◄──────────  collect ratings (local now, community later)
```

A rating of **5** = a good suggestion the user liked (a *positive* label); a low
rating = a *negative* label. Aggregated, these become the training/evaluation
signal for choosing and improving the recommender.

## 3. Guiding decisions (from our first tuning round)

| Decision | Choice | Implication |
|---|---|---|
| Project character | **Rigorous *and* shippable** | Research-grade methodology + metrics, delivered as a real in-app feature. |
| Where feedback lives | **Local-first now, community backend later** | Prototype the loop with local data; prove it before building the shared service. |
| Which model to train | **[OPEN] — decided in the Preliminary Phase** | We instrument + collect first, then choose the model from evidence (§7). |

## 4. Research question & success criteria

**RQ (draft, [OPEN] for refinement):** *Can explicit community ratings (1–5) on
suggestions generated from a user's playlists be used to select and train a
recommender that produces measurably better suggestions than the current
streaming-similarity / LLM-curated baseline?*

**Success looks like:**
- **Offline:** a model predicts held-out ratings better than baseline (e.g. lower
  MAE/RMSE) and ranks better (e.g. higher NDCG@k / hit-rate).
- **Online:** the **average rating of suggestions goes up** versus baseline, in a
  controlled comparison.
- **Shippable:** the loop is a usable feature, not just a notebook.

## 5. Scope & non-goals

**In scope:** suggestion generation conditioned on a user's playlists; per-track
1–5 rating capture; attributed logging of suggestions; a preliminary
data-collection + model-selection phase; a chosen model integrated back into the
app; later, a community feedback service + online evaluation.

**Non-goals (for now):** audio playback; building our own music catalog; heavy
distributed training infrastructure; a public product launch.

## 6. Phased roadmap

> Ordering reflects *local-first*, and front-loads instrumentation so the
> Preliminary Phase has data to reason about.

- **Phase 1 — Instrument the loop (local).** Add per-track 1–5 rating to Discover;
  define & persist the **data schema** (§8) locally, including full suggestion
  *attribution* (which model/version, seed context, rank, score, explanation).
- **Phase 2 — Preliminary Phase (exploration & model selection). [current focus once Phase 1 emits data]**
  Collect a first dataset; define metrics & evaluation protocol; establish
  baselines; benchmark candidate modeling approaches (§7); **choose the model**
  with evidence. *This is where the deferred model decision is made.*
- **Phase 3 — Train & integrate.** Build the chosen model; re-rank suggestions with
  it; run an in-app A/B (baseline vs model) measuring rating uplift.
- **Phase 4 — Community backend.** A shared service (API + DB) that aggregates
  ratings across users, with accounts + consent; online evaluation at scale.
- **Phase 5 — Continuous improvement.** Scheduled retraining, model versioning,
  monitoring, drift/bias checks.

## 7. Modeling — candidates to evaluate in the Preliminary Phase

The model is **[OPEN]**; the Preliminary Phase compares these and picks one on
evidence (this *is* "choosing the right model"):

- **Baselines:** streaming "similar artists" ordering; current **LLM-curator**
  ordering. (Everything must beat these to justify itself.)
- **Learned re-ranker:** features of (user taste, candidate track) → predicted
  rating; re-orders candidates. Tractable with modest data.
- **Collaborative filtering:** community user×track rating matrix
  (matrix factorization / embeddings). Strong with many raters, weak when sparse.
- **LLM preference-tuning:** ratings → preference pairs (DPO) or examples (SFT) to
  tune an LLM recommender. Powerful, data/compute-heavy.

**Selection criteria:** offline metric wins **and** feasibility (data volume,
compute, latency) **and** online uplift. We expect to *start simple* (re-ranker /
baselines) and graduate to CF / LLM-tuning only if data and gains justify it.

## 8. Data model (the critical early artifact)

Defined locally now, but **designed to port to the community backend unchanged**.
Two core records:

- **Suggestion event** — `id`, `user_id` (pseudonymous), `created_at`, `provider`,
  `seed_context` (snapshot/hash of the seed playlists/favorite artists),
  `model_id` + `model_version`, `candidate_track_id` (+ a snapshot of its features),
  `rank`, `score`, `explanation`. *Attribution is mandatory — without it we can't
  compare models.*
- **Rating event** — `id`, `suggestion_id` (FK), `user_id`, `track_id`,
  `rating` (1–5), `rated_at`, optional context (e.g. already-known? added?).

**[OPEN]** exact fields, feature snapshot contents, and identity/pseudonymization
scheme.

## 9. Evaluation plan

- **Offline:** rating prediction (MAE/RMSE); ranking (NDCG@k, MAP, hit-rate@k);
  proper **temporal + per-user splits** (no leakage).
- **Online:** average suggestion rating, acceptance/add rate; **A/B** baseline vs
  model; some **exploration** so we don't only learn about what we already show.
- **Bias controls:** exposure/feedback-loop bias (we only see ratings on shown
  items), popularity bias, rating subjectivity/noise.
- **Rigor:** report uncertainty (CIs), pre-register metrics before Phase 3.

## 10. Ethics, consent & privacy

Because we collect human feedback and (later) aggregate it:
- **Local-first** minimizes exposure early; nothing leaves the device until the
  community phase, which is **opt-in with informed consent**.
- **Pseudonymous** user ids; data minimization; clear purpose; deletion/opt-out.
- If pursued academically, follow the institution's **ethics/IRB** process and
  GDPR-style principles.
- Respect streaming providers' terms; store only what the research needs.

## 11. Risks & open questions

- **[OPEN] Model choice** — deferred to the Preliminary Phase (§7), by design.
- **Cold start & sparsity** — few users/ratings early; content/LLM features must
  carry the start.
- **Feedback-loop bias** — needs exploration + careful eval.
- **Community recruitment / data volume** — how many raters, how fast? Affects which
  models are even viable.
- **Label noise** — 1–5 is subjective; consider rating guidance / calibration.
- **Provider ToS** and the reverse-engineered Tidal/Qobuz APIs may constrain scale.

## 12. Next steps

1. Iterate on this document (especially the **[OPEN]** items and the RQ).
2. Lock the **Phase-1 data schema** (§8) — it's the foundation everything else
   depends on.
3. Then (and only then) begin Phase-1 implementation.

> Nothing here is coded yet — this is the project definition we refine together.
