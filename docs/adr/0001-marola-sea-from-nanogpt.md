# ADR 0001: marola-sea is built from karpathy/nanoGPT, copied as is

| | |
|---|---|
| **Status** | Proposed (2026-10-14), by the owner's order |
| **Issue** | [marola-ml#48](https://github.com/marola-dev/marola-ml/issues/48) |
| **Supersedes** | the Llama 3.2 base of marola-sea in MIP-0025 and MIP-0048: an umbrella MIP must record it |

## Context

marola-sea was a fine-tune of a vendored base model: Llama 3.2 through a Modelfile (Tier 1) and
QLoRA and DPO adapters (Tier 2, [the fine-tune page](../3-development_finetune.md)). Marola owned
neither the base weights nor the code that made them. The owner, 14 October 2026: "changing the
base vendored model for full ownership marola", "This will be only way of building marola-sea
model (and distributing it)".

Three starting points were read on 14 October 2026:

| Source | Licence | Usable |
|---|---|---|
| [akitaonrails/microgpt](https://github.com/akitaonrails/microgpt) at `2e4f32774b03` | none: no LICENSE file, none in `pyproject.toml`, GitHub's licence API answers 404 | no: all rights reserved. Read, credited, not copied |
| Karpathy's microgpt gist (`8627fe009c40f57531cb18360106ce95`) | none on the gist; its comments ask for one | no |
| [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) at `3adf61e154c3` | MIT, Copyright (c) 2022 Andrej Karpathy | yes, with the notice kept |

nanoGPT's README says it is "very old and deprecated" next to its successor,
[nanochat](https://github.com/karpathy/nanochat) (MIT too). nanochat is a whole chat pipeline
for a GPU node; nanoGPT is one small GPT that trains on a CPU, which is where marola-sea starts.

## Decision

1. Copy nanoGPT's code as is into `sea/nanogpt/`, with its LICENSE byte for byte, and a header in
   every other file: the fork date, the commit and the MIT notice. `sea/FORK.tsv` records each
   file's upstream sha256; `sea/fork_check.py` (in `just quality`) holds the copy to it.
2. Marola's own code beside it, in `sea/`: the corpus dataset, the training settings, the check.
3. marola-sea is built only this way: `just marola-gpt-prepare`, `just marola-gpt-train` (named
   marola-gpt since [ADR 0002](0002-marolagpt-and-the-restricted-licence.md)).

## Consequences

- **Ownership, said exactly.** Marola owns its changes and the weights it trains. The code that
  came from nanoGPT stays Andrej Karpathy's under MIT, edited or not: the licence lets marola use,
  change and distribute it, and requires its notice in every copy. An edit does not move that
  copyright; it adds marola's on top.
- `ruff` skips `sea/nanogpt/`: a copy as is keeps its own style, and `fork_check.py` guards it.
- The Llama path (`finetune/`, its publish workflow (removed in ADR 0002), the Ollama model `marola-llama3.2` the
  app uses) still exists. Whether it is removed, and what the app runs until marola-sea from
  nanoGPT can replace it, is the umbrella MIP's to decide; nothing else in the app changes here.
- The first run is a start, not a model: 15 080 characters of corpus, a 0.80M-parameter GPT,
  validation loss 2.485 at its best ([`sea/README.md`](../../sea/README.md)).
