# Theoretical Foundations: Large Language Models and Their Fit for Music Recommendation

> **Project:** Music Manager — Goal 2 (community-labeled recommendation).
> **Phase:** 0 — Theoretical foundations. **Status:** v0.1 draft for iteration.
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
Attention(Q, K, V) = softmax( Q Kᵀ / √d ) V
```

Several such attention "heads" run in parallel (multi-head attention), letting the
model attend to different kinds of relationships at once. Because attention is
order-agnostic, **positional information** is injected separately (positional
encodings). Attention layers are interleaved with token-wise feed-forward layers,
and the whole stack uses residual connections and normalization to train stably.

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
  a high rating versus a low one is a preference signal.
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
  plays); explicit feedback is rarer and valuable but costlier to collect.
- **Learning to rank** trains models to *order* candidates well, optimizing ranking
  metrics directly — a natural framing for "re-rank the suggestions."

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
- Ouyang et al., 2022 — *Training Language Models to Follow Instructions with Human Feedback* (InstructGPT/RLHF).
- Hoffmann et al., 2022 — *Training Compute-Optimal Large Language Models* (Chinchilla).
- Wei et al., 2022 — *Emergent Abilities of Large Language Models.*
- Schaeffer et al., 2023 — *Are Emergent Abilities of Large Language Models a Mirage?*
- Rafailov et al., 2023 — *Direct Preference Optimization.*
- Dettmers et al., 2023 — *QLoRA: Efficient Finetuning of Quantized LLMs.*
- Koren et al., 2009 — *Matrix Factorization Techniques for Recommender Systems.*
- Hu et al., 2008 — *Collaborative Filtering for Implicit Feedback Datasets.*
- Geng et al., 2022 — *Recommendation as Language Processing (P5).*
- Bao et al., 2023 — *TALLRec: Tuning LLMs for Recommendation.*
- Wu et al., 2023 — *A Survey on Large Language Models for Recommendation.*

> Citations are pointers for study, not reproductions of the works. Next iteration:
> tighten the research question (PROJECT.md §4) in light of §8, then resume the
> deferred Phase-1 data-schema design.
