# AGENTS.md

Instructions for any AI coding agent working in **marola-ml**. This is the repo layer
(MIP-0070 §5.1): the workspace rules live in the umbrella's
[AGENTS.md](https://github.com/marola-dev/marola/blob/main/AGENTS.md); this file says what this
repo is and where it differs.

<!-- invariants:start -->
## Org invariants

Non-negotiable in every marola repo; a repo may make these stricter, never looser (MIP-0070 §5.1).

- **Cost and deployment safety**: never provision or deploy a paid cloud resource without explicit human confirmation first ([AGENTS.md](AGENTS.md#cost--deployment-safety-hard-rule)).
- **No secrets in code**: never hardcode a key/connection string/secret; `.env.example` holds placeholders only ([AGENTS.md](AGENTS.md#cost--deployment-safety-hard-rule)).
- **The agent-ready gate**: an agent may only begin implementation on an issue carrying `agent-ready` ([AGENTS.md](AGENTS.md#issue-tracking-hard-rule)).
- **The three commit trailers**: commits carry three trailers and nothing else — `Tested:`, `Cost:`, and `Co-Authored-By: Claude <noreply@anthropic.com>` ([AGENTS.md](AGENTS.md#attribution-and-cost-accounting-hard-rule)).
- **Phase discipline**: work one phase at a time; never start a later phase before the current one is done ([AGENTS.md](AGENTS.md#phase-discipline-hard-rule)).
<!-- invariants:end -->

## What this repo is

marola's offline Python, none of it on the app's request path: the DSPy prompt compile, the
fine-tune (marola-sea), and the benchmark gate with its kept runs.

- `dspy/`: compiles the summarizer and reviewer prompts the app replays
  (`recommendation_prompt.json`, `review_prompt.json`). It calls an LLM many times, so it is a
  manual step.
- `finetune/`: the Tier 1 Modelfile, the Tier 2 QLoRA + DPO recipe, dataset builders, merge/export,
  the Hugging Face publish. Torch, peft and trl stay behind lazy imports, so every script's
  `--self-test` runs on the standard library.
- `scripts/benchmark_gate.py` and `docs/benchmarks/`: the promotion gate and the kept runs it
  compares against. `scripts/analyze_training.py`, `scripts/marola-sea-pull.sh`: a training run's
  report, and pulling the published model into Ollama.
- `Dockerfile.local`: Ollama with `marola-llama3.2` and the benchmark's embedder
  (`nomic-embed-text:v1.5`) in its store, built and gated by `docker-local.yml`;
  `scripts/benchmark.sh` runs the pinned app image's `--benchmark` against it.

## What it consumes and produces (MIP-0070 §5.4)

| Direction | Contract | Pinned by |
|---|---|---|
| app → ml | The app image, whose `--benchmark` is the benchmark runner | `marola-image` (`ghcr.io/marola-dev/marola-app:jvm-<sha>@sha256:<digest>`, `scripts/app-image.sh`) |
| app → ml | The resources tarball `ml-resources-<tag>.tar.gz` on an app release: the compiled prompts, `sea_lore.json`, `benchmark_questions.json`. marola-app's `release.yml` attaches it to each `v*` tag | `resources.version`; `just resources-fetch` unpacks it into `.tmp/resources` |
| corpus → ml | `marola-corpus-<tag>.tar.gz` | `corpus.version`; `just corpus-fetch` unpacks it into `.tmp/knowledge` |
| ml → app | The compiled prompts, as a PR to the app's `core/src/main/resources/` (`compile-prompt.yml`) | The files in the app |
| ml → users | `ghcr.io/marola-dev/marola-ml:local` (`docker-local.yml`); marola-sea on Hugging Face (`marola-sea-publish.yml`) | Image tag; model repo |
| ml → umbrella | `README.md` and `docs/` (`notify-umbrella.yml`); `api-docs.tar.gz`, pdoc of `finetune/` and `scripts/`, on each `v*` release (`release.yml`) | Pulled by the aggregator |

No workflow here builds the app or reads its tree. Bump `marola-image` and `resources.version`
together: the gate fails a run whose question ids differ from the pinned question set.

## Commands

```bash
nix develop                  # the lint tools, the devkit's tools, the CUDA venv helpers; links .devkit
just quality                 # every gate CI runs (fetches the pinned corpus and resources first)
just finetune-dataset        # finetune/data/{train,eval}.jsonl
just benchmark               # the pinned app image's --benchmark on the local Ollama, then the gate
just compile-prompt          # DSPy into .tmp/compiled (costs LLM calls; see dspy/README.md)
just api-docs                # <out>/python/ pdoc, as api-docs.yml's CI check runs it
```

The app's own recipes (`just run`, `just e2e`, `just ask`) run in an app checkout.

## Cost & deployment safety (hard rule)

As in the umbrella, and stricter here, because this repo is where the money is:

- `compile-prompt.yml` compiles against a model Ollama serves inside the job, never a paid
  endpoint. A local `just compile-prompt` against a paid model needs a human's go-ahead first.
- `marola-sea-publish.yml` trains for hours on the self-hosted `marola-sea` runner and uploads to
  Hugging Face, which cannot be taken back. Dispatch only, by a human; it may never gain a trigger a
  pull request can reach (`ci.yml`'s `runners` job enforces it). It waits on the HF_TOKEN secret,
  and separately on the marola-sea runners being registered for this repo. marola already has the
  tag `marola-sea-v1`, which this repo's history does not carry: dispatch the first publish here
  with `major_version: 2`.
- An agent does not dispatch workflows, create tags or releases (`.claude/settings.json` denies
  `gh workflow run`, `gh release` and `git tag`).

## Issue tracking (hard rule)

An agent starts work only on an issue carrying `agent-ready`, in this repo (MIP-0070 §5.7).

## Attribution and cost accounting (hard rule)

Commits carry `Tested:`, `Cost:` and `Co-Authored-By: Claude <noreply@anthropic.com>`, as in the
umbrella. A benchmark or training run an agent drives counts toward the feature's `Cost:`.

## Phase discipline (hard rule)

The phase list is the umbrella's `docs/PHASES.md`. ML work serves the current phase.

## Style

Python 3.12, ruff (`ruff.toml`); standard library only outside the training scripts' lazy imports.
Every script keeps a `--self-test`, and a change to one starts with a failing case there. A gate
that reads an input fetches it first and fails on an empty one. Shell: `set -euo pipefail`,
shellcheck-clean, status output on stderr. Comments only for why, a trap, or a pointer, as the
umbrella's AGENTS.md spells out.
