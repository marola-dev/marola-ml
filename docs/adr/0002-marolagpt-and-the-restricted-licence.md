# ADR 0002: the model is marolaGPT, and marola-ml's licence restricts it to marola

| | |
|---|---|
| **Status** | Proposed (2026-10-14), by the owner's order |
| **Builds on** | [ADR 0001](0001-marola-sea-from-nanogpt.md), the fork of nanoGPT |
| **Needs** | the written agreement of every contributor whose code is relicensed (below), and an umbrella MIP for the licence of a marola repository |

## Context

The owner, 14 October 2026: "state this repo as a nanoGPT fork from Karpathy. This repository will
contain efforts of building its own model from scratch. the name of distribution will be
marolaGPT. Make sure all the tooling, marola-corpus ingest to HuggingFace publish. account used
will still be h0ffmann for while. And LICENSE of marola-ml, will be restricted rights to marola
contributors. Not allowed any distribution of marolaGPT outside of marola-dev repository. There
are many other forks out there and this is educational distribution of a model (SML)".

## Decision

1. **The name.** The model trained in `sea/` is marolaGPT; its releases are `marolaGPT-<version>`.
2. **The chain.** `just marolagpt <version>`: the pinned corpus, the dataset, training from random
   weights, the release directory (weights, vocabulary, card, licence, checksums), then the upload
   to `h0ffmann/marolaGPT` on Hugging Face, a dry run unless `--yes`. In CI,
   `marolagpt-publish.yml`, dispatched by hand, a dry run by default.
3. **The licence.** `LICENSE` becomes the marola-ml Restricted License: marola-dev's contributors
   may use the repository inside marola-dev; others may read and cite it; marolaGPT may not be
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
  `h0ffmann/marolaGPT` as marola's channel while the owner keeps it so. `publish_hf.py` creates the
  repository private; making it public is the owner's act on Hugging Face.
- **No workflow artifact.** On a public repository any GitHub user can download a workflow's
  artifacts, so `marolagpt-publish.yml` keeps none.
- **Wording.** The licence was written by an agent, from the owner's words, and not by a lawyer.
