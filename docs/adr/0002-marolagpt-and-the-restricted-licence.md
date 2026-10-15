# ADR-0002: the model is marola-gpt, and marola-ml's licence restricts it to marola

| | |
|---|---|
| **Status** | Proposed (2026-10-14), by the owner's order; its licence (decision 3) and the name marolaGPT superseded by [ADR 0003](0003-mit-again-and-the-name-marola-gpt.md) the same day |
| **Builds on** | [ADR 0001](0001-marola-sea-from-nanogpt.md), the fork of nanoGPT |
| **Needs** | the written agreement of every contributor whose code is relicensed (below), and an umbrella MIP for the licence of a marola repository |

## Context

The owner, 14 October 2026: "state this repo as a nanoGPT fork from Karpathy. This repository will
contain efforts of building its own model from scratch. the name of distribution will be
marola-gpt. Make sure all the tooling, marola-corpus ingest to HuggingFace publish. account used
will still be h0ffmann for while. And LICENSE of marola-ml, will be restricted rights to marola
contributors. Not allowed any distribution of marola-gpt outside of marola-dev repository. There
are many other forks out there and this is educational distribution of a model (SML)".

## Decision

1. **The name.** The model trained in `sea/` is marola-gpt; its releases are `marola-gpt-<version>`.
2. **The chain.** `just marola-gpt <version>`: the pinned corpus, the dataset, training from random
   weights, the release directory (weights, vocabulary, card, licence, checksums), then the upload
   to `h0ffmann/marola-gpt` on Hugging Face, a dry run unless `--yes`. In CI,
   `marola-gpt-publish.yml`, dispatched by hand, a dry run by default. It replaces
   `marola-sea-publish.yml`, the Llama path's publish, which is removed (the owner's choice,
   14 October 2026).
3. **The licence.** `LICENSE` becomes the marola-ml Restricted License: marola-dev's contributors
   may use the repository inside marola-dev; others may read and cite it; marola-gpt may not be
   distributed outside marola-dev's channels.

## Consequences

- **What the licence cannot change.** The code in `sea/nanogpt/` stays under Karpathy's MIT
  License: anyone may still take nanoGPT itself under MIT. A version published before the change
  stays MIT. The licence binds what marola owns: its own code and the weights it trains.
- **The contributors.** On 14 October 2026, `git shortlog` on `main` lists commits by Matheus
  Hoffmann and Bruno Guilhermo de Barros Valério (24), besides bots. Code that a contributor wrote
  under MIT can be relicensed only with that contributor's agreement: each one's written agreement
  is a condition of merging this change.
- **Hugging Face is a channel outside the organisation.** The licence names
  `h0ffmann/marola-gpt` as marola's channel while the owner keeps it so. `publish_hf.py` creates the
  repository private; making it public is the owner's act on Hugging Face.
- **No workflow artifact.** On a public repository any GitHub user can download a workflow's
  artifacts, so `marola-gpt-publish.yml` keeps none.
- **Wording.** The licence was written by an agent, from the owner's words, and not by a lawyer.
