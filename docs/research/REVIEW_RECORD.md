# Review Record — v0.1 → v0.2

A provenance note for the Goal-2 research documents
([PROJECT.md](../PROJECT.md), [LLM_FOUNDATIONS.md](LLM_FOUNDATIONS.md)).

## Method

The v0.1 drafts were put through an **adversarial multi-agent peer review**: nine
expert reviewers (one per dimension — LLM theory, preference-tuning math, recommender
systems, research methodology, evaluation, citations, cross-doc consistency, ethics,
and a completeness critic) each raised findings; **every finding was then
independently verified by a skeptical agent** (default-reject) to filter nitpicks and
false positives; the survivors were synthesized into a prioritized report.

- Findings raised → **verified as real: 43**, rejected: 28.
- All 23 foundations citations were checked; all verified correct.

## Verdict

The research direction was judged **sound** — a genuinely empirical RQ, an
evidence-deferred model choice, accurate LLM/Transformer foundations, and a rigorous
RLHF/DPO treatment. The gaps were **load-bearing under-specification**, not factual
errors.

## What changed in v0.2

**LLM_FOUNDATIONS.md**
- §3: corrected the attention denominator **√d → √d_k** (with the variance rationale);
  "order-agnostic" → **permutation-equivariant**.
- §6.1: named the DPO **partition function β·log Z(x)** and why it cancels; separated
  **reward-regression (keeps ordinal 1–5)** from **KTO (binary, needs thresholding)**;
  split **IPO** (anti-over-optimization) from **ORPO** (reference-free, single-stage).
- §7: added **two-tower / neural CF** and **sequential recommenders**
  (GRU4Rec/SASRec/BERT4Rec) as capacity-matched classical contenders.
- Citations: IPO year 2023; expanded DPO title; anchored Hu (2008); added
  Covington/Yi/Hidasi/Kang–McAuley/Sun/Joachims.

**PROJECT.md**
- §4: replaced the ill-posed "comparable capacity" with an **equal deployment budget**
  (RAM + latency, ≥2 budget points; learning capacity explicitly *not* equalized);
  quantified H1/H2/H3 (threshold **N**, **TOST** equivalence for H2); named **NDCG@k**
  primary; added a formal problem statement + shared candidate pool.
- §6: per-phase **exit gates**.
- §7: added **most-popular / random** baselines; defined **LLM-curator** as a frozen
  config distinct from the LLM arm; added two-tower/neural-CF and sequential contenders;
  specified the two-stage hybrid + candidate-pool control.
- §8: schema gains the ⚠ unrecoverable fields — **`propensity`**, **`arm`/`assignment`/
  exploration-policy**, **inference config**, mandatory **familiarity** flags, and a
  **consent record**.
- §9: pre-registration moved **before Phase 2**; **off-policy estimation (IPS/SNIPS/DR)**
  + propensity; **position-bias** control (team-draft interleaving + position propensity);
  **familiarity/MNAR** controls + **discovery-only** primary online endpoint; split
  mechanics (global `T`, frozen CF matrix, cold-start stratum); **power analysis +
  mixed-effects + stopping rule + go/no-go**; LLM determinism; offline↔online arbiter.
- §10: operationalized **consent artifact + invariant, IRB gate, pseudonymity≠anonymity,
  dataset scope-of-use, erasure propagation, GDPR specifics, participant transparency**.
- §11: a **per-provider ToS check** (incl. Spotify's prohibition on training ML on its
  content) to resolve before the schema locks.

## Open decisions surfaced — resolved in v0.3

- **Dataset scope of use** → **private now, publishable path** (neutral IDs + open
  features + opt-in publish-consent make a later MovieLens-style release possible) (§10).
- **Erasure** → **de-link + tombstone** (delete identity↔pseudonym map + exclude from
  future training; frozen experiments keep de-identified rows) (§10).
- **Provider ToS** → **resolved by design**: decouple the dataset from provider catalog
  data via **ISRC/MusicBrainz keying + open-dataset features**; services are the
  listen/rate surface only (§8, §11).
- **Deployment budget** → reference machine + RAM/latency budget, two LLM points
  (~3–4B, ~7–8B), classical arm within the same budget (§4).
- Still **[pre-register]** (data-dependent, fixed from the Phase-1 pilot): threshold `N`,
  TOST margin, MDE.
- Remaining **[OPEN]**: ethics/IRB path; exact open-feature sources/fields.
