<div align="center">

<img alt="A small wave that curls once and runs on as a line of letters, each a dot, growing: an original drawing for marola-ml" src="drawings/marola-ml.svg" width="300"/>

# marola-ml

<sub>a fork of <a href="https://github.com/karpathy/nanoGPT">karpathy/nanoGPT</a> · the home of <b>marola-gpt</b> · <a href="#marola-gpt">the model</a> · <a href="#from-the-corpus-to-hugging-face">the chain</a> · <a href="#licence">licence</a> · <a href="#fork-notice">fork notice</a></sub>

[![ci](https://img.shields.io/github/actions/workflow/status/marola-dev/marola-ml/ci.yml?branch=main&label=ci&style=flat-square)](https://github.com/marola-dev/marola-ml/actions/workflows/ci.yml)
[![fork of nanoGPT](https://img.shields.io/badge/fork%20of-karpathy%2FnanoGPT%20%403adf61e-1682D4?style=flat-square)](https://github.com/karpathy/nanoGPT/tree/3adf61e154c3fe3fca428ad6bc3818b27a3b8291)
[![marola-gpt: an educational SLM](https://img.shields.io/badge/marola-gpt-educational%20SLM-F2B705?style=flat-square)](#marola-gpt)
[![licence: MIT](https://img.shields.io/badge/licence-MIT-1682D4?style=flat-square)](#licence)

A fork of Andrej Karpathy's nanoGPT where [marola](https://github.com/marola-dev/marola) builds
its own small language model from scratch: **marola-gpt**, trained from random weights on marola's
corpus of sourced ocean and marine-safety notes. There are many forks of nanoGPT; this one is an
educational distribution of a small language model (an SLM), made in the open and kept by marola.
</div>

## marola-gpt

marola-gpt is a character-level GPT in nanoGPT's code, trained on
[marola-corpus](https://github.com/marola-dev/marola-corpus) at the release `corpus.version` pins.
It is marola's from the first weight: no base model is downloaded.

| Release | Corpus | Model | Trained | Best validation loss |
|---|---|---|---|---|
| a local build, 2026-10-14 (not published) | v0.1.0: 15 080 characters, 87 distinct | 4 layers, 4 heads, width 128; 826 240 parameters | 1 000 steps on a CPU, 99.7 s | 2.4854 at step 600 |

Its text is word-shaped noise for now: the corpus is small enough to memorise, and the model
overfits after step 600. That is the honest start of an educational model, not an assistant.
Its text is never advice about the sea. **The first release on Hugging Face will be 0.0.1.**

**Where it is distributed.** On Hugging Face at `huggingface.co/h0ffmann/marola-gpt`, under the
owner's account for now (14 October 2026), public, under the MIT License like this repository.

## From the corpus to Hugging Face

The chain has five steps: the pinned corpus, the dataset, training from random weights, the
release directory, the upload to `h0ffmann/marola-gpt`. It reaches Hugging Face in two ways, and
**never on a merge**:

| Way | You run | What publishes |
|---|---|---|
| [By tag](#release-by-tag-just-sea-release) (CD) | `just sea-release` | `marola-gpt-publish.yml`, on the pushed tag `marola-gpt-vX.Y.Z` |
| [By hand](#manual-hugging-face-release) | `just marola-gpt-publish <v> --yes` on your machine | your own `--yes` |

An upload cannot be taken back. Both ways refuse a release whose files do not match their
checksums, and an agent starts neither: no tag, no dispatch, no `--yes`.

### Release by tag: `just sea-release`

The pattern that publishes is a tag `marola-gpt-vX.Y.Z` on a commit of main. `just sea-release`
makes it: it takes the highest `marola-gpt-v*` tag and increments it (the first is `0.0.1`), checks
that main is clean, level with origin, and green in CI, then tags and pushes. The tag starts
[`marola-gpt-publish.yml`](.github/workflows/marola-gpt-publish.yml) on a GitHub-hosted runner,
which trains marola-gpt from the pinned corpus, packages it and uploads it to `h0ffmann/marola-gpt`,
tagged `vX.Y.Z` there. It needs the `HF_TOKEN` secret, a fine-grained Hugging Face token with write
access to that repository.

```bash
git switch main && git pull
just sea-release --dry-run             # every check, and the tag it would push; pushes nothing
just sea-release                       # the next patch: marola-gpt-v0.0.1, then 0.0.2, ...
just sea-release minor                 # or major, or an exact version: just sea-release 0.3.0
gh run list --workflow marola-gpt-publish.yml --limit 1    # follow the publish
```

A tag that is not on main is refused by the workflow. Merges, however many, publish nothing until
the next tag.

### Manual Hugging Face release

To build and upload from your own machine, logged in to Hugging Face as `h0ffmann`
(`huggingface-cli login`, or `HF_TOKEN` in the environment). It needs Nix, `just`, and a Python with
[`sea/requirements.txt`](sea/requirements.txt) installed, named by `SEA_PYTHON`.

```bash
nix develop
export SEA_PYTHON=/path/to/python      # torch (CPU: download.pytorch.org/whl/cpu), numpy, tiktoken, huggingface_hub

just marola-gpt-prepare                 # 1. marola-corpus at its pin -> sea/nanogpt/data/marola_corpus/
just marola-gpt-train                   # 2. nanoGPT from random weights (sea/config/train_marola_gpt.py)
just marola-gpt-sample                  #    look at what it learned
just marola-gpt-package 0.0.1           # 3. sea/release/marola-gpt-0.0.1/: weights, vocabulary, card, licence, checksums
just marola-gpt-publish 0.0.1           # 4. a dry run: what would go, and where
just marola-gpt-publish 0.0.1 --yes     # 5. the upload to h0ffmann/marola-gpt (created public), tagged v0.0.1
just marola-gpt 0.0.1                   # steps 1 to 4 at once, ending in the dry run
```

`--key=value` after `just marola-gpt-train` overrides a setting, for example
`just marola-gpt-train --max_iters=3000`. Use the same version as a `marola-gpt-v*` tag when the
release should match one, and run it from that tag's checkout so the model card names its commit.
The workflow can also be run by hand (Actions → "marola-gpt publish"): a dry run unless you untick
`dry_run`.

<details>
<summary>What runs where</summary>

| Step | File | Whose |
|---|---|---|
| fetch the corpus | `scripts/corpus-fetch.sh` | marola's |
| the dataset | [`sea/prepare_corpus.py`](sea/prepare_corpus.py) | marola's |
| the training settings | [`sea/config/train_marola_gpt.py`](sea/config/train_marola_gpt.py) | marola's |
| training and sampling | [`sea/nanogpt/train.py`](sea/nanogpt/train.py), [`sample.py`](sea/nanogpt/sample.py), [`model.py`](sea/nanogpt/model.py) | Andrej Karpathy's, MIT, copied as is |
| the release | [`sea/package.py`](sea/package.py) | marola's |
| the upload | [`sea/publish_hf.py`](sea/publish_hf.py) | marola's |
| the copy stays as is | [`sea/fork_check.py`](sea/fork_check.py), [`sea/FORK.tsv`](sea/FORK.tsv) | marola's |

</details>

## The rest of marola-ml

The offline Python behind marola, from before the fork. None of it runs when the app answers a
question.

- [`dspy/`](https://github.com/marola-dev/marola-ml/tree/main/dspy): the prompt compile. The
  `compile prompt` workflow runs it on an Ollama model inside the job and opens a PR in the app
  with the two compiled files ([how to run it](docs/3-development_prompt-compile.md)).
- [`finetune/`](https://github.com/marola-dev/marola-ml/tree/main/finetune): the older path, a
  Llama 3.2 fine-tune (Tier 1, a Modelfile; Tier 2, QLoRA SFT and DPO) that makes the
  `marola-llama3.2` model the app uses today. [Its page](docs/3-development_finetune.md) says it is
  superseded for marola's own model; an umbrella MIP decides its end.
- [`docs/benchmarks/`](https://github.com/marola-dev/marola-ml/blob/main/docs/benchmarks/2026-09-05.md):
  the kept benchmark runs. `scripts/benchmark_gate.py` fails a new run that falls more than 0.05
  below the best of them, or below the plain prompt
  ([the gate's doc](docs/3-development_benchmark-gate.md)).
- `Dockerfile.local`: Ollama with `marola-llama3.2` already in its store, published as
  `ghcr.io/marola-dev/marola-ml:local` once it clears the gate (`docker-local.yml`).
- The Llama path has no publish workflow any more: `marola-sea-publish.yml` was replaced by
  `marola-gpt-publish.yml` on 14 October 2026. `just finetune-publish` still uploads by hand.

```bash
nix develop
just quality            # every gate CI runs, the fork check and marola-gpt's self-tests included
just finetune-dataset   # the Llama path's training set, from the pinned resources and corpus
just benchmark          # the pinned app image's --benchmark on your Ollama, then the gate
```

## Contracts

Pinned releases, never another repo's tree: the app image (`marola-image`), the app's resources
tarball (`resources.version`) and the corpus (`corpus.version`). `just corpus-fetch` and
`just resources-fetch` unpack the last two into `.tmp/`. The compiled prompts go back to the app as
a PR; marola-gpt goes to Hugging Face. The full table, with what pins each, is in
[AGENTS.md](https://github.com/marola-dev/marola-ml/blob/main/AGENTS.md#what-it-consumes-and-produces-mip-0070-54).

## Docs

- [Design](docs/1-design.md): the three jobs, none on the request path, and the module map.
- [Libraries](docs/2-libraries.md): each library, model and pinned tool, and why.
- [Development](docs/3-development.md): environment, GPU, the self-hosted runner, CI, secrets,
  cost and who may run what, publishing, the pins.
- [The prompt compile](docs/3-development_prompt-compile.md),
  [the fine-tune](docs/3-development_finetune.md),
  [the benchmark gate](docs/3-development_benchmark-gate.md): each job, how to run it.
- [External evaluation](docs/3-development_external-eval.md): the models and benchmarks marola asks
  an evaluation provider to run, and the terms every provider is held to.
- Decisions: [ADR 0001](docs/adr/0001-marola-sea-from-nanogpt.md), the fork of nanoGPT;
  [ADR 0002](docs/adr/0002-marolagpt-and-the-restricted-licence.md), the model's chain (its licence part
  superseded); [ADR 0003](docs/adr/0003-mit-again-and-the-name-marola-gpt.md), MIT again and the name
  marola-gpt.
- [API docs](https://docs.marola.dev/5-Repos/marola-ml/api-docs/python/): pdoc of `finetune/` and
  `scripts/`, from the `api-docs` branch `ci.yml`'s `api-docs` job rewrites on each push to main.
- [AGENTS.md](AGENTS.md): the rules for agents working here.

## Gemini review

Request the reviewer `marola-dev/gemini` on a pull request (sidebar → Reviewers, or
`gh pr edit <N> --add-reviewer marola-dev/gemini`). `marola-gemini-bot` posts one review with at
most 10 inline comments tagged `[high]`/`[medium]`/`[low]`, then pushes one commit with the fixes
it is sure of, after `python3 -m compileall -q finetune scripts dspy` passes. Request it again
after new commits for a fresh review. It runs only when asked, reviews fork pull requests without
pushing to them, and never edits `.github/`. `.github/workflows/gemini.yml` calls the devkit's
[`gemini-review`](https://github.com/marola-dev/marola-devkit/blob/main/docs/4-reference_workflows.md#gemini-review)
workflow.

## Credits

- **Andrej Karpathy**, for nanoGPT (MIT), the code marola-gpt is trained with.
- **Fabio Akita** ([@akitaonrails](https://github.com/akitaonrails)), whose
  [microgpt](https://github.com/akitaonrails/microgpt) gave marola the idea of a GPT trained from
  scratch on one machine, measured honestly. None of its code is here: it had no licence on the
  day of the fork ([marola-site#146](https://github.com/marola-dev/marola-site/issues/146)).
- The layout of this page follows
  [marola-research's](https://github.com/marola-dev/marola-research). The drawing at the top is an
  original, made for this repository.

## Licence

**MIT** ([`LICENSE`](LICENSE), Copyright (c) 2026 marola.dev): the code of this repository and
marola-gpt, the model it trains, may be used, changed and distributed by anyone, with the notice
kept. The code in `sea/nanogpt/` is Andrej Karpathy's, under nanoGPT's own MIT License
(`sea/nanogpt/LICENSE`, Copyright (c) 2022 Andrej Karpathy).

From 14 October 2026 to the change back ([ADR 0003](docs/adr/0003-mit-again-and-the-name-marola-gpt.md)),
`main` carried a restricted licence; no release was made under it.

## Fork notice

This repository's history has three parts.

1. **Marola's.** marola-ml was split out of the [umbrella](https://github.com/marola-dev/marola)
   (MIP-0070), with marola's history filtered to these files: the prompt compile, the benchmark
   gate, and a model fine-tuned from Llama 3.2 (`finetune/`).
2. **The fork of nanoGPT, 14 October 2026.** The code of
   [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) at commit
   `3adf61e154c3fe3fca428ad6bc3818b27a3b8291` was copied as is into `sea/nanogpt/`, under its MIT
   License (Copyright (c) 2022 Andrej Karpathy, kept in `sea/nanogpt/LICENSE`). Every copied file
   says so in its first lines, and [`sea/FORK.tsv`](sea/FORK.tsv) records what each was upstream.
   From that day marola's own model is built only from it.
3. **Marola's again, on top.** The same day, the model got its name, marola-gpt. The repository
   briefly carried a restricted licence and went back to MIT before any release
   ([ADR 0003](docs/adr/0003-mit-again-and-the-name-marola-gpt.md)). Every change marola makes after
   the fork is marola's, under MIT, and so are the weights it trains. The code that came from
   nanoGPT stays Andrej Karpathy's under MIT, and its notice stays with it.
