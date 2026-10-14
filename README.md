# marola-ml

The offline Python behind [marola](https://github.com/marola-dev/marola): the DSPy step that
compiles the prompts the app replays, the fine-tune that produces marola-sea (MIP-0025, MIP-0048),
and the benchmark gate that decides whether a model is promoted. None of it runs when the app
answers a question.

It is one of the marola repos under the [umbrella](https://github.com/marola-dev/marola)
(MIP-0070), and its history before the split is marola's, filtered to these files.

**marola-sea is now built from [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT), copied
as is into [`sea/`](sea/README.md)**: a GPT that marola trains from random weights on its own
corpus ([ADR 0001](docs/adr/0001-marola-sea-from-nanogpt.md)). The fork notice at the end of this
page tells the history.

**Status:** the prompt compile (`compile-prompt.yml`, dispatched by hand) and the benchmark gate
(`docker-local.yml`, on a push to main touching the model or the gate) run in CI. marola-sea has
trained only at the `tiny` preset; its publish waits on the HF_TOKEN secret and the marola-sea
runners.

## Run it

```bash
nix develop
just quality            # every gate CI runs
just finetune-dataset   # the training set, from the pinned resources and corpus
just benchmark          # the pinned app image's --benchmark on your Ollama, then the gate
```

## Repo map

- [`sea/`](sea/README.md): marola-sea. nanoGPT copied as is into `sea/nanogpt/` (MIT, Andrej
  Karpathy), with marola's corpus dataset and training settings beside it (`just sea-prepare`,
  `just sea-train`, `just sea-sample`).
- [`dspy/`](https://github.com/marola-dev/marola-ml/tree/main/dspy): the prompt compile. The
  `compile prompt` workflow runs it on an Ollama model inside the job and opens a PR in the app
  with the two compiled files ([how to run it](docs/3-development_prompt-compile.md)).
- [`finetune/`](https://github.com/marola-dev/marola-ml/tree/main/finetune): Tier 1 (a Modelfile)
  and Tier 2 (QLoRA SFT + DPO) of marola-sea, with the dataset builders and the Hugging Face
  publish. [Its page](docs/3-development_finetune.md) is the honest status of each tier.
- [`docs/benchmarks/`](https://github.com/marola-dev/marola-ml/blob/main/docs/benchmarks/2026-09-05.md): the kept benchmark runs.
  `scripts/benchmark_gate.py` fails a new run that falls more than 0.05 below the best of them, or
  below the plain prompt — [the gate's doc](docs/3-development_benchmark-gate.md) has the
  re-baselining process.
- `Dockerfile.local`: Ollama with `marola-llama3.2` already in its store, published as
  `ghcr.io/marola-dev/marola-ml:local` once it clears the gate (`docker-local.yml`).
- `marola-sea-publish.yml`: train and publish marola-sea, by hand only. It waits on two things,
  each tracked in its own issue: the HF_TOKEN secret; the marola-sea runners registered at org
  level for this repo.

## Contracts

Pinned releases, never another repo's tree: the app image (`marola-image`), the app's resources
tarball (`resources.version`) and the corpus (`corpus.version`). `just corpus-fetch` and
`just resources-fetch` unpack the last two into `.tmp/`. The compiled prompts go back to the app as
a PR; marola-sea publishes to Hugging Face. The full table, with what pins each, is in
[AGENTS.md](https://github.com/marola-dev/marola-ml/blob/main/AGENTS.md#what-it-consumes-and-produces-mip-0070-54).

## Gemini review

Request the reviewer `marola-dev/gemini` on a pull request (sidebar → Reviewers, or
`gh pr edit <N> --add-reviewer marola-dev/gemini`). `marola-gemini-bot` posts one review with at
most 10 inline comments tagged `[high]`/`[medium]`/`[low]`, then pushes one commit with the fixes
it is sure of, after `python3 -m compileall -q finetune scripts dspy` passes. Request it again after new commits for a fresh review. It runs only when
asked, reviews fork pull requests without pushing to them, and never edits `.github/`. `.github/workflows/gemini.yml`
calls the devkit's [`gemini-review`](https://github.com/marola-dev/marola-devkit/blob/main/docs/4-reference_workflows.md#gemini-review)
workflow.

## Docs

- [Design](docs/1-design.md): the three jobs, none on the request path, and the module map.
- [Libraries](docs/2-libraries.md): each library, model and pinned tool, and why.
- [Development](docs/3-development.md): environment, GPU, the self-hosted runner, CI, secrets,
  cost and who may run what, publishing marola-sea, the pins.
- [The prompt compile](docs/3-development_prompt-compile.md),
  [the fine-tune](docs/3-development_finetune.md),
  [the benchmark gate](docs/3-development_benchmark-gate.md): each job, how to run it.
- [External evaluation](docs/3-development_external-eval.md): the models and benchmarks marola asks
  an evaluation provider to run, and the terms every provider is held to.
- [API docs](https://docs.marola.dev/5-Repos/marola-ml/api-docs/python/): pdoc of `finetune/` and
  `scripts/`, from the `api-docs` branch `ci.yml`'s `api-docs` job rewrites on each push to main.
- [AGENTS.md](AGENTS.md): the rules for agents working here.

## Fork notice

This repository's history has three parts.

1. **Marola's.** marola-ml was split out of the [umbrella](https://github.com/marola-dev/marola)
   (MIP-0070), with marola's history filtered to these files: the prompt compile, the benchmark
   gate, and a marola-sea fine-tuned from Llama 3.2 (`finetune/`).
2. **The fork of nanoGPT, 14 October 2026.** The code of
   [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) at commit
   `3adf61e154c3fe3fca428ad6bc3818b27a3b8291` was copied as is into `sea/nanogpt/`, under its MIT
   License (Copyright (c) 2022 Andrej Karpathy, kept in `sea/nanogpt/LICENSE`). Every copied file
   says so in its first lines, and [`sea/FORK.tsv`](sea/FORK.tsv) records what each was upstream.
   From that day marola-sea is built only from it.
3. **Marola's again, on top.** Every change marola makes to `sea/` after the fork is marola's, and
   the weights it trains are marola's. The code that came from nanoGPT stays Andrej Karpathy's
   under MIT, and its notice stays with it.

The idea of starting from a small GPT trained from scratch came from Fabio Akita's
[microgpt](https://github.com/akitaonrails/microgpt); none of its code is here, because it had no
licence on the day of the fork (marola-ml#48).
