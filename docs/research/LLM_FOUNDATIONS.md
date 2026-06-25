# Theoretical Foundations: Large Language Models and Their Fit for Music Recommendation

> **Project:** Music Manager — Goal 2 (community-labeled recommendation).
> **Phase:** 0 — Theoretical foundations. **Status:** v0.2 (incorporates adversarial peer review).
>
> This is a background study written in the style of a paper's *Foundations /
> Related Work* chapter. Its purpose is not only to explain what a Large Language
> Model (LLM) is, but to let us reason rigorously about whether an LLM is the right
> instrument for our task, and how it would be trained or tuned. Claims are
> attributed to the literature (§9). The prose is our own.

---

## Abstract

We review the theory of Large Language Models: the language-modeling objective,
the Transformer architecture that made scaling practical, and the pretrain-then-adapt
paradigm under which modern systems are built. We describe — conceptually — how one
would construct such a model "from zero," and why, in practice, work begins from
pretrained *foundation models* rather than from scratch. We then survey the
techniques used to adapt a pretrained model to a task (prompting, retrieval,
supervised fine-tuning, preference optimization, and parameter-efficient tuning).
Finally, we contrast LLMs with classical recommender systems and assess their fit
for our problem — generating and ranking music suggestions from a user's playlists
under explicit 1–5 feedback — concluding that the question is empirical and that a
**hybrid** design is the most promising hypothesis to test in later phases.

## 1. Introduction

Our project suggests music to users from their playlists and improves those
suggestions using explicit ratings (§Goal 2 of [PROJECT.md](../PROJECT.md)). A
recurring temptation is to treat "use an LLM" as the answer. Before committing, we
must understand what an LLM *is*, what it is good and bad at, and how it would be
trained or tuned — so that the model choice (deferred to the Preliminary Phase) is
made on evidence rather than hype.

## 2. What is a language model?

A **language model (LM)** assigns probabilities to sequences of symbols (tokens).
Given a sequence of tokens `w₁ … w_T`, the chain rule of probability factorizes the
joint probability into a product of *next-token* conditional probabilities:

```
P(w₁ … w_T) = Π_t  P(w_t | w₁ … w_{t-1})
```

Modeling each conditional `P(w_t | context)` is the entire task. Early LMs estimated
these from counts over fixed windows (n-grams); they were brittle and could not
generalize across surface forms. Neural LMs replaced counts with learned functions.
A key enabling idea was the **distributed word representation** — embedding tokens as
vectors so that semantically related tokens lie near one another (Bengio et al.,
2003; Mikolov et al., 2013). Recurrent networks (RNNs/LSTMs) then modeled longer
contexts, but processed tokens sequentially and struggled to carry information across
long ranges.

**Implication for us:** an LM is fundamentally a *predictor of likely continuations*,
not a database of facts and not, by construction, a personalization engine. This
shapes everything below.

## 3. The Transformer

The **Transformer** (Vaswani et al., 2017) is the architecture underlying essentially
all modern LLMs. Its core mechanism is **self-attention**, which lets every token's
representation be updated as a weighted combination of all other tokens'
representations in the context, with the weights computed from the content itself.

Conceptually, each token produces a *query*, a *key*, and a *value* vector. The
similarity between a token's query and other tokens' keys determines how much each
*value* contributes:

```
Attention(Q, K, V) = softmax( Q Kᵀ / √d_k ) V
```

The denominator is **√d_k**, the per-head key/query dimension (under multi-head,
`d_k = d_model / h`). The scaling offsets the dot product's variance, which grows with
`d_k`; without it, large-magnitude scores push the softmax into saturated regions with
vanishing gradients.

Several such attention "heads" run in parallel (multi-head attention), letting the
model attend to different kinds of relationships at once. Because self-attention is
**permutation-equivariant** (reorder the inputs and the outputs reorder identically —
it has no inherent notion of position), **positional information** is injected
separately (positional encodings). Attention layers are interleaved with token-wise
feed-forward layers, and the whole stack uses residual connections and normalization
to train stably.

Modern LLMs are typically **decoder-only** and **autoregressive**: they predict the
next token given only the tokens before it (a causal mask), and generate text by
sampling one token at a time and feeding it back in. The amount of prior text the
model can condition on is the **context window**. The advantage over RNNs is that
self-attention is highly parallelizable and models long-range dependencies directly —
which is precisely what made training at scale feasible.

**Tokenization.** Text is first split into tokens, usually *subword* units (e.g.,
byte-pair encoding; Sennrich et al., 2016) so that rare or novel words decompose into
known pieces. Tokens — not words — are the model's atomic unit, which matters when we
later reason about cost, context limits, and how the model "sees" artist or track
names.

## 4. From a model to a *Large* language model

An LLM is a Transformer LM scaled up along three axes — **parameters, data, and
compute** — and trained with a **self-supervised** objective: predict the next token
on enormous corpora of text. No human labels are required for this *pretraining*
stage; the supervision is the text itself (the "label" for each position is simply
the token that actually came next). Cross-entropy between the predicted distribution
and the true next token is minimized by gradient descent.

Two empirical findings motivate the "large":

- **Scaling laws.** Loss falls predictably as parameters, data, and compute grow
  (Kaplan et al., 2020; Hoffmann et al., 2022, who re-balanced the data-vs-size
  trade-off). This made scale a deliberate strategy, not an accident.
- **In-context learning and emergent behavior.** At sufficient scale, models perform
  tasks they were never explicitly trained for, simply by being shown a few examples
  in the prompt (Brown et al., 2020). Some capabilities appear to emerge with scale
  (Wei et al., 2022), though how to measure "emergence" is debated (Schaeffer et al.,
  2023).

Because such models are trained once at great expense and then reused for many tasks,
they are called **foundation models** (Bommasani et al., 2021).

## 5. Building one "from zero" — and why nobody really does

Conceptually, constructing an LLM from scratch requires:

1. **Data.** Collect and clean a very large, diverse text corpus; deduplicate and
   filter for quality and safety.
2. **Tokenizer.** Train a subword vocabulary on that corpus.
3. **Architecture.** Choose a decoder-only Transformer and its size (layers, width,
   heads, context length).
4. **Pretraining.** Optimize next-token prediction over the corpus — the
   compute-dominant step, typically requiring large clusters of accelerators for
   weeks to months.
5. **Evaluation & iteration.** Track loss and downstream benchmarks; adjust.

In practice, step 4 is out of reach for almost everyone: it demands capital,
engineering, and energy at industrial scale. The field therefore operates by
**transfer learning** — start from a released pretrained model and *adapt* it
(§6). "From zero" is thus best understood as a conceptual reference point: it clarifies
what the pretrained weights already encode (broad statistical knowledge of language
and the world as reflected in text) and, by contrast, what *we* must still supply
(task framing, domain data, personalization, and feedback). **For our project, this
means the realistic levers are adaptation and the surrounding system — not training a
base model.**

## 6. Adapting a pretrained model: the training/tuning landscape

Given a pretrained model, there is a spectrum of ways to specialize it, from
*no weight changes* to *full retraining*. Ordered roughly by cost:

- **Prompting / in-context learning.** Steer behavior purely through the input —
  instructions and a few worked examples (zero-/few-shot). No training; fast to
  iterate; bounded by the context window and the base model's abilities (Brown et
  al., 2020).
- **Retrieval-Augmented Generation (RAG).** Retrieve relevant external data at
  inference time and place it in the prompt, grounding outputs in up-to-date or
  private information without changing weights (Lewis et al., 2020). Relevant to us:
  a candidate track list or a user's taste profile can be *retrieved* and given to
  the model rather than learned into it.
- **Supervised fine-tuning (SFT).** Continue training the weights on curated
  input→output examples for the target behavior (e.g., instruction tuning). Requires
  labeled data and compute, and risks overfitting or "catastrophic forgetting."
- **Preference / alignment tuning.** Optimize the model against *preferences* rather
  than single gold answers. **RLHF** trains a reward model from human comparisons and
  then optimizes the policy with reinforcement learning (Christiano et al., 2017;
  Ouyang et al., 2022). **Direct Preference Optimization (DPO)** achieves a similar
  effect by optimizing directly on preference pairs, avoiding a separate RL loop
  (Rafailov et al., 2023). **This family is conceptually closest to our 1–5 ratings**:
  a high rating versus a low one is a preference signal. **Expanded in §6.1.**
- **Parameter-efficient fine-tuning (PEFT).** Update only a small set of added
  parameters (e.g., low-rank adapters, **LoRA**; Hu et al., 2021; quantized variant
  **QLoRA**, Dettmers et al., 2023), making fine-tuning feasible on modest hardware
  while keeping most weights frozen.
- **Embeddings / representation use.** Instead of generating text, use the model to
  produce vector representations of items (tracks, artists, descriptions) for
  similarity search or as features in a downstream model — often the cheapest way to
  exploit an LLM's semantic knowledge inside a classical pipeline.

**Key point for the project:** "train the model" is not one thing. Our explicit
ratings could feed (a) prompt construction (few-shot exemplars of liked items), (b) a
downstream ranking model that consumes LLM *embeddings*, or (c) preference tuning
(SFT/DPO) of an LLM recommender — at very different costs and data requirements.

## 6.1 Deep dive: learning from human preferences (RLHF, DPO, and pointwise variants)

Because our 1–5 ratings are *human judgements of suggestions*, the machinery for
turning human feedback into model updates is the most relevant family to understand
in depth. Two paradigms dominate — Reinforcement Learning from Human Feedback (RLHF)
and Direct Preference Optimization (DPO) — alongside *pointwise* variants that fit
numeric ratings especially well.

### Setup and notation

A **policy** `π_θ(y | x)` is the model we want to improve: given a context `x` (e.g.,
a user's taste and a candidate item) it assigns probability to an output `y` (e.g., a
chosen recommendation). We keep a frozen **reference policy** `π_ref` — typically the
supervised-fine-tuned (SFT) model — as an anchor. Human feedback arrives either as
**comparisons** (output `y_w` "wins" over `y_l`) or **pointwise** labels (an output is
good/bad, or carries a numeric score — like our 1–5).

### RLHF — reward modeling + reinforcement learning

RLHF (Christiano et al., 2017; Ouyang et al., 2022) has three stages:

1. **SFT.** Fine-tune the base model on demonstrations to obtain a sensible starting
   policy `π_ref`.
2. **Reward model (RM).** Collect human *comparisons* and train a reward model
   `r_φ(x, y)` so preferred outputs score higher. The standard choice uses the
   Bradley–Terry preference model, giving the loss
   `L_RM = − E[ log σ( r_φ(x, y_w) − r_φ(x, y_l) ) ]`,
   where `σ` is the logistic function. The RM thus *learns to imitate human judgement*.
3. **RL optimization.** Optimize the policy to maximize expected reward while staying
   near the reference, via a KL-regularized objective
   `max_θ  E_{y∼π_θ}[ r_φ(x, y) ]  −  β · KL( π_θ(·|x) ‖ π_ref(·|x) )`,
   usually with Proximal Policy Optimization (PPO; Schulman et al., 2017).

**Why the KL anchor matters:** without it, the policy can exploit imperfections in the
learned reward (give absurd outputs high reward — "reward hacking"), so the constraint
keeps it close to trusted behavior. **Costs/risks:** three-to-four models in play
(policy, reward, reference, plus a value network in PPO), online sampling during
training, and well-known instability and hyperparameter sensitivity. Powerful, but
operationally heavy.

### DPO — preferences without a reward model or RL

Direct Preference Optimization (Rafailov et al., 2023) begins from the *same*
KL-regularized objective but exploits the fact that it has a closed-form optimal
policy. For that optimum, the reward can be re-expressed in terms of the policy itself:
`r(x, y) = β · log [ π_θ(y|x) / π_ref(y|x) ] + β · log Z(x)`,
where `Z(x)` is the partition function of the optimal policy (it depends on `x`, not
`y`). Because the `β · log Z(x)` term is the **same for `y_w` and `y_l`**, it cancels
in the Bradley–Terry *difference* below — which is precisely why both the reward model
*and* the otherwise-intractable `Z(x)` disappear.

Substituting this *implicit reward* into the Bradley–Terry preference loss makes the
reward model vanish; the objective becomes a simple supervised loss over preference
pairs:
`L_DPO = − E_{(x, y_w, y_l)} [ log σ( β·log(π_θ(y_w|x)/π_ref(y_w|x)) − β·log(π_θ(y_l|x)/π_ref(y_l|x)) ) ]`.

In words: **increase the model's relative likelihood of the preferred output over the
dispreferred one**, scaled by `β` and anchored to the reference. No separate reward
model, no RL loop — a classification-style loss over pairs.

**Trade-offs:** DPO is simpler, more stable, and cheaper, and is frequently competitive
with RLHF. But it is *offline* (it learns only from a fixed preference set, with no
online exploration), is sensitive to how pairs are sampled, and can over-optimize; `β`
sets how strongly the reference anchors the update.

### Pointwise ratings: KTO and reward regression

Our signal is **pointwise** (a 1–5 score per suggestion), not naturally pairwise. Two
options:

- **Convert to pairs.** Within one context, a higher-rated suggestion "wins" over a
  lower-rated one, yielding preference pairs usable by DPO/RLHF.
- **Use pointwise directly.** Two sub-options that differ in what they preserve:
  - **Reward/utility regression** on the raw 1–5 score keeps the full *ordinal*
    information (a 5 is meaningfully better than a 4).
  - **KTO** (Kahneman–Tversky Optimization; Ethayarajh et al., 2024) consumes a
    *binary* desirable/undesirable label, so a 1–5 scale must first be **thresholded**
    (e.g., ≥4 = desirable) — discarding ordinal detail that regression retains.

Two related preference methods, often grouped but distinct: **IPO** (Azar et al.,
2023) adds a regularizer that keeps DPO from over-optimizing when preferences are
near-deterministic; **ORPO** (Hong et al., 2024) is **reference-free** — it folds an
odds-ratio preference penalty into the SFT loss in a single stage, dropping `π_ref`
entirely (attractive under our low-infrastructure, local-first constraint).

### What this means for our project

Our ratings map cleanly onto this machinery — which is exactly why it warranted depth:

- If we pursue an **LLM recommender**, the no-reward-model, no-RL routes are most
  attractive: **reward/utility regression** if we want to keep the full 1–5 ordinal
  signal, or **DPO/KTO** if we convert ratings to preference pairs / a binary
  threshold. (ORPO is appealing operationally for dropping the reference model.)
- But the *same* ratings can instead train a **classical re-ranker or reward model by
  regression**, with far less machinery.

Whether a preference-tuned LLM is worth its added cost over a simple learned ranker is
precisely the question our adapted research hypothesis poses (PROJECT.md §4).

## 7. A short recommender-systems primer (for contrast)

Our task is, at its core, a **recommendation** problem, a field with its own mature
toolkit:

- **Content-based** methods recommend items similar to what a user liked, using item
  features. (Our current candidate generation — streaming "similar artists" — is
  content/graph-based.)
- **Collaborative filtering (CF)** learns from the *community's* interaction matrix:
  if users who agree with you liked an item, you probably will too. Matrix
  factorization learns latent user and item vectors whose dot product predicts the
  rating (Koren et al., 2009). CF is powerful with many users but suffers from
  **cold start** and **sparsity**.
- **Explicit vs. implicit feedback.** Our **1–5 ratings are explicit feedback** — a
  classic, information-rich signal (the setting of the well-known MovieLens datasets
  and the Netflix Prize). Much modern recsys instead uses implicit signals (clicks,
  plays; e.g., Hu et al., 2008); explicit feedback is rarer and valuable but costlier
  to collect.
- **Learning to rank** trains models to *order* candidates well, optimizing ranking
  metrics directly — a natural framing for "re-rank the suggestions."
- **Neural & two-tower recommenders.** Beyond 2009-era matrix factorization, modern
  classical recsys uses neural collaborative filtering and **two-tower (dual-encoder)**
  models that embed users and items into a shared space for fast approximate-nearest-
  neighbor retrieval (Covington et al., 2016; Yi et al., 2019), plus feature-rich
  models (wide-and-deep, factorization machines, DeepFM). A two-tower neural retriever
  is, notably, the most **capacity-matched** classical counterpart to a local LLM under
  our fairness constraint (PROJECT.md §4).
- **Sequential / session-based recommenders.** Because a playlist is an *ordered*
  signal, models that consume sequences are natural contenders: **GRU4Rec** (Hidasi et
  al., 2016) and the self-attention models **SASRec** (Kang & McAuley, 2018) and
  **BERT4Rec** (Sun et al., 2019). The last two are themselves attention sequence
  models, structurally analogous to a decoder-only LLM (§3) — so a small,
  domain-trained sequence recommender is another capacity-matched rival. (Caveat: our
  signal is *explicit pointwise ratings*, not pure next-track continuation, so this is
  one contender, not the presumptive winner.)

There is also a growing literature on **LLMs *for* recommendation** — using them as
zero-shot rankers, as feature/embedding generators, or fine-tuned on interaction data
(e.g., Geng et al., 2022; Bao et al., 2023; and recent surveys such as Wu et al.,
2023). The consensus is nuanced: LLMs bring semantic knowledge and cold-start
strength but do not, by themselves, replace collaborative signal.

## 8. Is an LLM the right model for *our* task?

We weigh the evidence for our specific problem: suggest music from a user's
playlists, then learn from explicit 1–5 ratings, starting local and small.

**Where an LLM is strong here:**
- **Semantic & world knowledge of music.** It "knows" relationships between artists,
  genres, eras, and moods from pretraining — useful for candidate generation and for
  explaining *why* a suggestion fits.
- **Cold start.** With few or no ratings (our early reality), an LLM can still reason
  from names and descriptions, where CF cannot.
- **Natural-language explanations.** It can articulate the rationale for a pick — a
  genuine product feature and a transparency aid.
- **Flexibility.** Zero-/few-shot adaptation lets us prototype without training.

**Where an LLM is weak or risky here:**
- **Not personalized by construction.** It models language, not *this user's* latent
  preferences; personalization must be engineered (prompting, retrieval, or tuning).
- **Hallucination & validity.** It may invent tracks, mis-attribute songs, or suggest
  items unavailable on the user's service; outputs must be validated against the real
  catalog.
- **Poor native fit for tabular feedback.** A matrix of 1–5 ratings is exactly what CF
  and learning-to-rank are built for; coercing it into an LLM (via preference tuning)
  is possible but data- and compute-hungry, and may be overkill at small scale.
- **Cost, latency, reproducibility.** Inference is comparatively expensive and
  nondeterministic, complicating controlled evaluation.

**Where classical recsys is strong:** efficient, well-understood evaluation, and
direct use of explicit ratings for personalization — but weak at cold start,
semantics, and explanation.

**Synthesis (a hypothesis, not a verdict).** The strengths and weaknesses are largely
*complementary*. The most promising design to test is a **hybrid**:

- LLM (or content/graph methods) for **candidate generation** and **explanation**,
  exploiting semantic knowledge and covering cold start;
- a **learned re-ranker or collaborative model** that consumes the **1–5 ratings** to
  **personalize** the ordering — the part LLMs do not natively provide;
- with the **LLM's embeddings** as one possible feature source bridging the two.

Crucially, "is an LLM the right model?" is **an empirical question**, and our project
is structured to answer it: the **Preliminary Phase** benchmarks these approaches
(baselines, learned re-ranker, CF, and LLM-based variants) against the collected
ratings on agreed metrics (PROJECT.md §7, §9). This document's role is to make that
comparison *informed* — to ensure we know what each option can and cannot do before
we measure it.

## 9. Implications for the project

1. Treat the LLM as **one component and one baseline among several**, not the
   foreordained answer.
2. Because personalization from explicit feedback is the LLM's weakest point and our
   central goal, **design the data and the re-ranking step deliberately** (the
   deferred Phase-1 schema work).
3. Prefer **cheap adaptation first** (prompting, retrieval, embeddings) and escalate
   to **fine-tuning / preference optimization** only if the data volume and measured
   gains justify it.
4. Whatever is used, **validate every suggestion against the real catalog** to
   neutralize hallucination.

## Glossary

- **Token** — atomic text unit (often a subword) the model reads and predicts.
- **Embedding** — a learned vector representation of a token or item.
- **Self-attention** — mechanism letting each token's representation depend on the
  others, weighted by learned content similarity.
- **Autoregressive** — generating one token at a time, each conditioned on the
  previous ones.
- **Pretraining** — large-scale self-supervised next-token training that yields a
  foundation model.
- **Fine-tuning / PEFT** — adapting (all / a small subset of) weights to a task.
- **RLHF / DPO** — aligning a model to human *preferences*.
- **RAG** — grounding generation in retrieved external data at inference time.
- **Collaborative filtering** — recommending from the community's interaction matrix.
- **Explicit feedback** — direct ratings (our 1–5), as opposed to implicit signals.

## References

Selected works (author, year, title) for follow-up reading:

- Bengio et al., 2003 — *A Neural Probabilistic Language Model.*
- Mikolov et al., 2013 — *Efficient Estimation of Word Representations in Vector Space* (word2vec).
- Sennrich et al., 2016 — *Neural Machine Translation of Rare Words with Subword Units* (BPE).
- Vaswani et al., 2017 — *Attention Is All You Need.*
- Devlin et al., 2019 — *BERT: Pre-training of Deep Bidirectional Transformers.*
- Kaplan et al., 2020 — *Scaling Laws for Neural Language Models.*
- Brown et al., 2020 — *Language Models are Few-Shot Learners* (GPT-3).
- Lewis et al., 2020 — *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.*
- Bommasani et al., 2021 — *On the Opportunities and Risks of Foundation Models.*
- Hu et al., 2021 — *LoRA: Low-Rank Adaptation of Large Language Models.*
- Christiano et al., 2017 — *Deep Reinforcement Learning from Human Preferences.*
- Schulman et al., 2017 — *Proximal Policy Optimization Algorithms* (PPO).
- Ouyang et al., 2022 — *Training Language Models to Follow Instructions with Human Feedback* (InstructGPT/RLHF).
- Ethayarajh et al., 2024 — *KTO: Model Alignment as Prospect Theoretic Optimization.*
- Azar et al., 2023 — *A General Theoretical Paradigm to Understand Learning from Human Preferences* (IPO; AISTATS 2024).
- Hong et al., 2024 — *ORPO: Monolithic Preference Optimization without Reference Model.*
- Hoffmann et al., 2022 — *Training Compute-Optimal Large Language Models* (Chinchilla).
- Wei et al., 2022 — *Emergent Abilities of Large Language Models.*
- Schaeffer et al., 2023 — *Are Emergent Abilities of Large Language Models a Mirage?*
- Rafailov et al., 2023 — *Direct Preference Optimization: Your Language Model is Secretly a Reward Model.*
- Dettmers et al., 2023 — *QLoRA: Efficient Finetuning of Quantized LLMs.*
- Koren et al., 2009 — *Matrix Factorization Techniques for Recommender Systems.*
- Hu et al., 2008 — *Collaborative Filtering for Implicit Feedback Datasets.*
- Covington et al., 2016 — *Deep Neural Networks for YouTube Recommendations* (two-tower).
- Yi et al., 2019 — *Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations* (two-tower retrieval).
- Hidasi et al., 2016 — *Session-based Recommendations with Recurrent Neural Networks* (GRU4Rec).
- Kang & McAuley, 2018 — *Self-Attentive Sequential Recommendation* (SASRec).
- Sun et al., 2019 — *BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations.*
- Joachims et al., 2017 — *Unbiased Learning-to-Rank with Biased Feedback* (position-bias propensity).
- Geng et al., 2022 — *Recommendation as Language Processing (P5).*
- Bao et al., 2023 — *TALLRec: Tuning LLMs for Recommendation.*
- Wu et al., 2023 — *A Survey on Large Language Models for Recommendation.*

> Citations are pointers for study, not reproductions of the works. Next iteration:
> tighten the research question (PROJECT.md §4) in light of §8, then resume the
> deferred Phase-1 data-schema design.
