# Music Manager — Project Definition

> **Status:** v0.2 — living draft, hardened after an adversarial peer review. This
> document is the subject of our design iterations; we tune it before writing any
> Goal-2 code. Decisions marked **[OPEN]** are still being settled; numeric values
> marked **[pre-register]** are fixed before the relevant phase, not now.

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

**RQ:** *On our explicit-feedback music task, which established recommendation
approach performs best, and how does an **LLM-based recommender** compare to it — can
the LLM (or an LLM-hybrid) match or beat the best classical recommender, and under
what conditions (data scale, cold start)?*

This is a **head-to-head comparison**: identify the strongest classical recommender on
our data, and pit it against an LLM-based one (or an **LLM-hybrid**).

**Formal framing.** Let `C` be the candidate universe (resolved, provider-native track
IDs). Each *arm* is a function that, given a user's taste/seed context, produces a
ranking over `C`. LLM free-text outputs are **resolved/normalized to IDs in `C`**
before scoring. All offline ranking metrics for the two arms are computed over the
**same candidate pool**; the online served-rating metric is a shared objective that
does not require a shared pool.

**Working hypotheses** (effect sizes are **[pre-register]**ed before Phase 2):
- **H1 (data-rich):** once a user has **≥ N** ratings (`N` [pre-register]), a classical
  model trained on the 1–5 feedback (learned re-ranker / CF / two-tower / sequential)
  outperforms the LLM on the primary ranking metric.
- **H2 (cold start / low data):** with **< N** ratings, the LLM **matches or beats**
  classical models by leveraging semantic/world knowledge. "Matches" is judged by a
  **TOST equivalence test** against a pre-registered margin — *not* a non-significant
  difference.
- **H3 (hybrid):** LLM candidate generation + a learned re-ranker beats either alone.

**Primary metric:** **NDCG@k** (ranking) is primary; rating-prediction error
(MAE/RMSE) is *diagnostic only* — it correlates poorly with top-k ranking (the
Netflix-Prize lesson noted in the foundations doc). Arms that emit only an ordering
(LLM, learning-to-rank) are scored on ranking metrics; MAE/RMSE is reported only for
arms emitting a calibrated 1–5 score.

**Fairness constraint — equal *deployment budget*, not "capacity".** "Capacity" is
**not commensurable** across an LLM and a classical recommender (a 7B LLM and a
~10⁵-parameter matrix-factorization model can share a RAM footprint yet differ in
expressivity by orders of magnitude), and *the axis one matches on silently decides the
result* (matching latency penalizes the autoregressive LLM → biases toward H1; matching
parameters forces an absurd CF model). We therefore:
- control a single, named **deployment budget** — **peak RAM + an inference-latency
  budget per recommendation** on target local hardware — rather than "capacity";
- state explicitly that **learning capacity/expressivity is *not* and *cannot* be
  equalized**, and that the LLM brings pretraining/world knowledge the classical model
  lacks (the H1-vs-H2 split is precisely designed to probe *when* that asymmetry helps);
- **report ≥ 2 budget points** (a smaller and a larger local LLM) so conclusions are
  not artifacts of one operating point;
- **[pre-register]** the axis and budget points before viewing online results.

**Driving the experience with both.** During evaluation the app serves suggestions from
**both arms**, with **user-level** randomized assignment and exposure-equalizing
interleaving (§9), so each gets rated. This yields the *paired, comparative* feedback
the RQ needs.

**Success looks like:**
- **Offline:** the winning arm beats the other on the **pre-registered primary metric**
  (NDCG@k), on proper splits with off-policy correction (§9), with reported CIs.
- **Online:** higher rating on the **discovery-only** primary endpoint (previously
  unknown items; §9) for the winning arm, in the controlled dual-arm A/B.
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

- **Phase 0 — Theoretical foundations (current task).** A paper-style background
  study of Large Language Models — what they are, how they work, how one is built
  "from zero" (conceptually) and adapted/tuned, and a critical assessment of
  whether an LLM is the right model for our recommendation task. See
  [research/LLM_FOUNDATIONS.md](research/LLM_FOUNDATIONS.md). *(The Phase-1
  data-schema questions are deferred until after this study.)*
- **Phase 1 — Instrument the loop (local).** Add per-track 1–5 rating to Discover;
  define & persist the **data schema** (§8) locally, including full suggestion
  *attribution* (model id/version + inference config, seed context, rank, **propensity**,
  arm/assignment, score, explanation). *Exit when:* attributed suggestion + rating
  events persist end-to-end and the schema is locked.
- **Phase 2 — Preliminary Phase (exploration & model selection).** **Pre-register**
  the protocol *first* (§9); collect a dataset; benchmark candidate approaches (§7) on
  the pre-registered primary metric with off-policy correction; **choose the model**
  with evidence. *This is where the deferred model decision is made.* *Exit when:*
  metrics/splits are pre-registered **and** ≥ 1 candidate beats the §7 baselines on the
  primary metric with CIs on a held-out confirmatory split.
- **Phase 3 — Train & integrate.** Build the chosen model; serve it as one arm against
  the comparison arm; run the in-app **dual-arm A/B** measuring rating uplift.
  *Exit when:* the A/B reaches the [pre-register]ed sample size with the result at the
  stated significance/equivalence.
- **Phase 4 — Community backend.** A shared service (API + DB) that aggregates ratings
  across users, with accounts + consent; online evaluation at scale. *Exit when:*
  consent-gated ingestion + aggregation run for ≥ 1 cohort.
- **Phase 5 — Continuous improvement.** Scheduled retraining, model versioning,
  monitoring, drift/bias checks.

## 7. Modeling — candidates to evaluate in the Preliminary Phase

The model is **[OPEN]**; the Preliminary Phase compares these and picks one on
evidence (this *is* "choosing the right model"):

**Baselines (everything must beat these to justify itself):**
- **Most-popular** — recommend globally popular tracks. Doubles as the §9 popularity-bias
  control.
- **Random** — calibrates the scale of NDCG/hit-rate and validates that exploration
  logging works.
- **Streaming "similar-artists" ordering** — the app's current content/graph candidate order.
- **LLM-curator (frozen)** — the app's prompt-only, zero-/few-shot LLM ranking with **no
  tuning and no learned re-ranker**, pinned to a fixed model id + version + prompt +
  decoding config. *This is distinct from the experimental LLM arm below*; beating it is
  necessary but not sufficient to answer the RQ.

**Classical contenders:**
- **Learned re-ranker** — features of (user taste, candidate track) → predicted rating;
  re-orders candidates. Tractable with modest data.
- **Collaborative filtering** — community user×track matrix (matrix factorization /
  embeddings). Strong with many raters, weak when sparse.
- **Two-tower / neural CF** — dual-encoder user/item embeddings + ANN retrieval; the most
  **deployment-budget-matched** classical counterpart to a local LLM.
- **Sequential recommender** — GRU4Rec / SASRec / BERT4Rec over the (ordered) playlist
  signal; a self-attention sequence model is structurally close to a decoder-only LLM.

**LLM contenders:**
- **LLM (prompted/RAG)** — the experimental LLM arm, personalized via retrieval of the
  user's taste/ratings.
- **LLM preference-tuned** — ratings → DPO/regression/KTO (foundations §6.1). Powerful,
  data/compute-heavy. *Ablation:* untuned-vs-tuned LLM isolates the value of tuning,
  separate from the §4 classical-vs-LLM head-to-head.

**Hybrid (H3):** the standard **two-stage retrieve-then-rank** design — LLM/content
candidate generation + a learned re-ranker. For any ranking comparison, hold the
candidate pool fixed across arms, **or** report candidate-generation recall@k separately
from re-ranking NDCG@k, so retrieval recall is not confounded with ranking quality.

**Selection criteria:** primary-metric win on a held-out confirmatory split **and**
feasibility within the deployment budget (§4) **and** online uplift. Off-policy-corrected
offline metrics **screen/narrow** candidates; the controlled dual-arm online uplift is
the **arbiter**. We expect to *start simple* (baselines / re-ranker) and graduate to
CF / two-tower / LLM-tuning only if data and gains justify it.

## 8. Data model (the critical early artifact)

Defined locally now, but **designed to port to the community backend unchanged**.
Several fields are **load-bearing and unrecoverable if not logged at collection time**
(flagged ⚠) — they must be in the Phase-1 schema, not added later.

- **Suggestion event** — `id`, `user_id` (pseudonymous), `created_at`, `provider`,
  `seed_context` (snapshot/hash of the seed playlists/favorite artists, time-stamped
  with **no post-cutoff information**), `candidate_track_id` (resolved to `C`) + a
  **time-stamped feature snapshot**, `rank`, `score`, `explanation`, and:
  - `model_id` + `model_version` — attribution; *without it we can't compare models*.
  - ⚠ **`propensity`** — probability this item was shown under the serving policy
    (needed for IPS/SNIPS off-policy estimation; §9).
  - ⚠ **`arm`** + **`assignment`** (exploit vs explore) + **exploration-policy id / ε** —
    which arm produced it and whether it was an exploration draw.
  - ⚠ **inference config** — exact model id + quantization/digest, `temperature`,
    `top_p`, `seed`, `prompt_template_hash` (LLM determinism; §9).
- **Rating event** — `id`, `suggestion_id` (FK), `user_id`, `track_id`,
  `rating` (1–5), `rated_at`, and **now mandatory** (they support the discovery RQ and
  the familiarity-bias control, §9): ⚠ **`already_known`** and ⚠ **`already_in_library`
  / `added`**.
- **Consent record** — `user_id`, **`consent_version`**, **`granted_at`**; invariant:
  **no upload/community ingestion without a valid consent record** (§10).

**[OPEN]** exact feature-snapshot contents (prefer **provider-neutral IDs + locally
derived features** over raw catalog metadata — see §11 ToS), and the
identity/pseudonymization scheme (the `user_id`↔identity map is stored **separately and
access-controlled**; see §10).

## 9. Evaluation plan

**Pre-registration (before Phase 2 — i.e., before *any* benchmarking).** Model
selection is the highest-degrees-of-freedom step (multiple model families × multiple
metrics = a garden of forking paths). Before looking at results we fix: the **primary**
vs secondary metrics, the **model-selection decision rule**, the **split scheme**, and a
final **held-out confirmatory split** (a fresh time-forward window) touched **once** for
the reported head-to-head. A lighter second pre-registration precedes the Phase-3 A/B.

- **Offline:** **NDCG@k primary** (MAP / hit-rate@k secondary); MAE/RMSE diagnostic
  only, for arms with a calibrated 1–5 output. Critically, logged ratings exist **only
  for shown items**, so naive offline metrics measure *exposure*, not model quality —
  we therefore estimate arm value with **off-policy estimators (self-normalized IPS /
  doubly-robust)** using the logged `propensity`. Apply a **multiplicity correction**
  across the family×metric grid.
- **Splits:** a **global temporal cutoff `T`** as the outer split, with per-user holdout
  in the post-`T` window; **freeze features *and* the CF interaction matrix to ≤ `T`**
  (forward-chaining — no future ratings leak into latent factors); an explicit
  **cold-start stratum** (users with `< N` prior ratings, reported separately, so H2 is
  testable); the *identical* split reused across all arms.
- **Online (the arbiter):** the randomized **dual-arm A/B**, **user-level**
  randomization. **Separate position bias from exposure bias:** equalize expected
  exposure via **team-draft interleaving** (or per-arm slot randomization), report each
  arm's **rank distribution** as a balance check, and apply **position-propensity**
  weighting (Joachims et al., 2017). **Primary online endpoint = rating on
  *previously-unknown* items** (genuine discovery, via `already_known`); all-items
  average is secondary. Report **rating-response rate per arm and per familiarity
  stratum**.
- **Bias controls:** exposure/off-policy bias (IPS/SNIPS/DR + logged propensity);
  position bias (interleaving + position propensity); **familiarity/recognizability
  bias** (an LLM may surface more recognizable artists, inflating its ratings for
  reasons unrelated to quality — hence the discovery-only primary endpoint); popularity
  bias (most-popular baseline); **MNAR** (voluntary ratings are non-random — condition
  on response/familiarity rather than comparing raw averages); rating subjectivity/noise.
- **Power & significance:** ratings within a user are **not independent**, so analyze
  with a **mixed-effects model (per-user random intercept)** — naive CIs are over-narrow.
  Before Phase 3, run a **power / sample-size calc** (target users and ratings/arm for a
  pre-stated MDE) and fix a **stopping rule** (fixed horizon or alpha-spending). A
  **go/no-go gate** ties to the §11 data-volume risk: if online power is insufficient,
  fall back to **offline-only** (off-policy-corrected) conclusions.
- **LLM determinism:** pin decoding (`temperature=0` / fixed `seed`) for the controlled
  comparison, or sample multiple completions and report variance; freeze model + config
  per comparison window (logged per §8).
- **Reconciliation:** persistent **offline↔online disagreement** signals residual
  logging bias to investigate, not a coin-flip.

## 10. Ethics, consent & privacy

Because we collect human feedback and (later) aggregate it, the principles below are
**operationalized**, not just named:

- **Consent artifact + invariant.** A versioned information sheet; a **`consent_version`
  / `granted_at`** record per user (§8); the hard invariant **no analysis-bound
  collection or upload without a valid consent record**. *(Even Phase-1/2 local ratings
  are analysis-bound — consent and the ethics gate precede them.)*
- **IRB / ethics timing gate.** If pursued academically, institutional ethics review (or
  a documented exemption) **precedes any analysis-bound collection** — it is a gate, not
  a footnote.
- **Pseudonymity ≠ anonymity.** A stable `user_id` + `seed_context` + ratings is a
  **re-identifiable fingerprint** (the Netflix-Prize re-identification lesson) and
  remains personal data under GDPR. Store the `user_id`↔identity map **separately and
  access-controlled**; hash/aggregate `seed_context`; minimize.
- **Scope of use [OPEN — your call].** The aggregated user×track rating matrix is the
  project's core asset. State its status — **private / shared-on-request / published** —
  its **license**, and a **redistribution-consent** clause. Note that *collect-to-train*
  vs *later-publish* is a **purpose change** requiring fresh consent.
- **Erasure propagation [OPEN].** Deletion/opt-out must propagate to **trained models,
  embeddings, frozen eval splits, and any published snapshot** — a real tension with the
  fixed splits + pre-registration above; resolve the policy explicitly.
- **GDPR specifics.** Lawful basis, controller/processor roles, retention period,
  purpose-limitation, and **special-category risk** (fine-grained music taste can proxy
  for religion/politics).
- **Participant transparency.** Tell users that suggestions are **experimental**, that
  ratings **train models**, and that some picks are **exploratory** (the §9 exploration
  draws).
- **Third-party LLM disclosure.** If any **non-local** LLM is ever used, user taste data
  leaves the device — disclose and consent, or keep the LLM local (our default).
- **Data minimization & ToS.** Store only what the research needs; see §11 for the
  per-provider Terms-of-Service analysis.

## 11. Risks & open questions

- **Provider Terms-of-Service [OPEN — resolve before Phase-1 schema lock].** We persist
  feature/seed-context snapshots and intend to train a recommender and (maybe) share a
  dataset — all of which provider terms may restrict. Run a **per-provider check**
  resolving, for **Spotify / Tidal / Qobuz**: (a) may we persist feature/seed snapshots,
  within caching limits? (b) may provider-derived data train/evaluate a recommender —
  **note Spotify's Developer Terms prohibit using Spotify Content to train ML/AI**?
  (c) may snapshots be aggregated/redistributed? (d) is reverse-engineered Tidal/Qobuz
  access itself a breach, and what is the mitigation? **Design lever:** prefer storing
  **provider-neutral IDs + locally derived features** over raw catalog metadata, and
  gate any dataset publication on confirmed redistribution rights. This is both a legal
  risk and a rigor risk (it can invalidate the pipeline or the shareability of results).
- **[OPEN] Model choice** — deferred to the Preliminary Phase (§7), by design.
- **Cold start & sparsity** — few users/ratings early; content/LLM features must carry
  the start (the cold-start stratum, §9, makes this measurable).
- **Feedback-loop / exposure / position bias** — addressed by logged propensity +
  exploration + off-policy estimation + interleaving (§8–§9); the residual risk is
  insufficient exploration.
- **Community recruitment / data volume** — how many raters, how fast? Gates the §9
  go/no-go (offline-only fallback if online power is short).
- **Label noise & MNAR** — 1–5 is subjective and ratings are non-random; mitigate with
  rating guidance/calibration and response/familiarity conditioning (§9).

## 12. Next steps

Ordered by dependency (schema-affecting and unrecoverable items first):

1. Resolve the **[OPEN]** decisions that *gate the schema*: the per-provider **ToS
   check** (§11), the **scope-of-use** position for the dataset (§10), and confirm the
   **ethics/IRB** path (§10).
2. Lock the **Phase-1 data schema** (§8) — including the ⚠ load-bearing fields
   (propensity, arm/assignment, inference config, familiarity, consent) that are
   **unrecoverable if not logged from day one**.
3. **Pre-register** the evaluation protocol (§9) before any benchmarking.
4. Then (and only then) begin Phase-1 implementation.

> Nothing here is coded yet — this is the project definition we refine together.
> v0.2 incorporates the verified findings of an adversarial peer review; the few
> genuine value-choices it surfaced are left as **[OPEN]** for you to set.
