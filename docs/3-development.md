# Development

How this repo is built, checked, run and published. How every marola repo reviews, tests and
ships is the umbrella's [dev flow](https://docs.marola.dev/3-Ways-of-working/DEV-FLOW/) and
[CI/CD](https://docs.marola.dev/3-Ways-of-working/CI-CD/); this page is what differs here. Each
job has its own page: [the prompt compile](3-development_prompt-compile.md),
[the fine-tune](3-development_finetune.md), [the benchmark gate](3-development_benchmark-gate.md).

## Environment

```bash
nix develop     # the lint tools, the devkit's tools, ollama, pdoc; the CUDA venv helpers on x86_64-linux
just quality    # every gate CI runs, docs-lint included; fetches the pinned corpus and resources first
```

Docker is the host's: `just benchmark` runs the pinned app image against the Ollama on
`localhost:11434`. The gates need nothing beyond the standard library; the compile and the
training each have their own `requirements.txt` ([libraries](2-libraries.md)). `just quality`
downloads the two pinned release tarballs once per pin, so it needs the network the first time.

## GPU

CPU is enough for the `tiny` preset; anything from `base` up wants a GPU
([the preset ladder](3-development_finetune.md#iterating-on-a-local-machine-the-small-model-ladder)).

- `just finetune-preflight preset=<name>` measures VRAM, RAM and the disk the run writes to, and
  prints a rough ETA, before a run starts.
- `just gpu-cache-setup` (once per host) adds the CUDA binary cache, so CUDA torch is fetched,
  not compiled. `just ml-venv` then builds the training venv from `finetune/requirements.txt`
  (`$HOME/.marola-ml-venv` unless `VENV_ROOT` says otherwise). Run training with its
  `bin/python-cuda`, never `bin/python`.
- `--device auto` uses CUDA when it is there; `--device cuda` fails loudly when torch sees no card
  rather than training on CPU for a day; `--device hybrid` spills what does not fit in VRAM into
  CPU RAM.
- `just temps` (the devkit's) watches CPU and GPU temperatures during a long run.

## The self-hosted runner

`marola-sea-publish.yml` is the only workflow that runs on a self-hosted runner, labelled
`marola-sea`, on the maintainer's machine. A public repo's self-hosted runner runs whatever a pull
request asks it to, so `workflow-runners` (in `ci.yml`'s `runners` job and in `just quality`) fails
when any other workflow names `self-hosted`, or when this one gains a trigger a pull request can
reach. Registering and running the runner are the devkit's recipes (`just runner-preflight`,
`just runners`, `just runner-up`); the devkit's
[runners page](https://github.com/marola-dev/marola-devkit/blob/v0.4.1/docs/4-reference_runners.md)
has the steps. The runners are not yet registered for this repo at org level: the publish waits on
that.

The job keeps its checkpoints (`../marola-checkpoints`) and its venv (`../marola-ml-venv`) outside
the checkout, so a run resumes from the last checkpoint and reuses the venv. It refuses to start
without `HF_TOKEN`, without a CUDA device, or when `preflight.py --strict` says the preset does
not fit.

## CI

| Workflow | Runs on | Does |
|---|---|---|
| `ci.yml` | every PR, push to main | the devkit's static-ci (actionlint, hadolint, shellcheck, docs-lint), python-ci (ruff and every `--self-test`), the runner guard, agents-check |
| `api-docs.yml` | every PR, push to main | `just api-docs` as a check; on main, the output goes to the `api-docs` branch |
| `docker-local.yml` | push to main touching the model, the pins or the gate; dispatch | build `Dockerfile.local`, benchmark it, move `:local` if the gate passes ([gate](3-development_benchmark-gate.md)) |
| `compile-prompt.yml` | dispatch | compile on an Ollama model inside the job, open a PR in marola-app |
| `marola-sea-publish.yml` | dispatch | train, merge, publish to Hugging Face, tag ([publishing](#publishing-marola-sea)) |
| `release.yml` | a `v*` tag | attach `api-docs.tar.gz` to the release |
| `notify-umbrella.yml` | push to main touching `README.md` or `docs/` | ask the umbrella to rebuild docs.marola.dev |
| `pr.yml`, `labels.yml` | PR events; dispatch | the PR body from its commits; the devkit's label set |

`ci.yml`'s static job clones the devkit at `v0.4.1` to run docs-lint, which static-ci has no input
for yet.

## Secrets

| Secret | Used by | For |
|---|---|---|
| `HF_TOKEN` | `marola-sea-publish.yml` | a fine-grained Hugging Face token with write access to the model repo; not set yet |
| `MAROLA_CROSS_REPO_PAT` | `compile-prompt.yml`, `notify-umbrella.yml` | the PR in marola-app; the umbrella dispatch (without it, a notice) |
| `GITHUB_TOKEN` | `docker-local.yml` | pushing to ghcr.io, and pulling the app image, a private package that has to grant this repo read access |

A local publish uses your own `huggingface-cli login`. No key goes in the repo.

## Cost and who may run what

This repo is where marola's money and irreversible steps are
([AGENTS.md](../AGENTS.md#cost--deployment-safety-hard-rule)).

| What | Cost | Who starts it |
|---|---|---|
| `just quality`, the self-tests, `just finetune-dataset` | free, seconds | anyone, an agent included |
| `just compile-prompt` on Ollama; `compile-prompt.yml` | free (a local model) | a person dispatches the workflow; locally, anyone |
| `just compile-prompt` on a paid model | cents to dollars | only after a human's go-ahead |
| `just benchmark`, `just finetune-train preset=tiny` | local compute, minutes | anyone; an agent's run counts toward the feature's `Cost:` |
| `marola-sea-publish.yml`, `just finetune-publish` | hours of training; an upload that cannot be taken back | a person, by hand |

An agent dispatches no workflow and creates no tag or release: `.claude/settings.json` denies
`gh workflow run`, `gh release` and `git tag`.

## Publishing marola-sea

`marola-sea-publish.yml` takes a preset (`tiny`, `small`, `qwen-4b`, `qwen-7b` or `qwen-14b`:
`base` needs a Hugging Face login the runner lacks, and `qwen-27b` has never run), builds the
dataset from the pinned corpus and resources, trains SFT then DPO, merges and exports the
`Q4_K_M` and `Q8_0` GGUFs, publishes them to `<owner>/<name>-GGUF` with the name and licence
`merge_export.py` planned, and only then pushes the tag `marola-sea-v<N>`. The training logs and
`analyze_training.py`'s report are the run's artifact for 90 days (`just training-logs`,
`just analyze-training`). Afterwards `just marola-sea-pull` pulls the published model into Ollama.

**Versions.** Left blank, `major_version` auto-increments past the highest `marola-sea-v*` tag in
this repo. marola already has `marola-sea-v1`, which this repo's history does not carry, so
dispatch the first publish here with `major_version: 2`. A pinned major/minor that already exists
fails before training starts.

What must be checked by hand before any upload (licence, the "Llama" name prefix, the model card)
is on [the fine-tune page](3-development_finetune.md#publishing-to-hugging-face-mip-0025-51-mip-0033-53).

## Pins

| Pin | Is | Bump |
|---|---|---|
| `marola-image` | the app image, tag and digest, whose `--benchmark` is the benchmark | with `resources.version`, in one PR: the gate fails a run whose question ids differ from the pinned set ([gate](3-development_benchmark-gate.md#bumping-the-pins)) |
| `resources.version` | the app release whose `ml-resources-<tag>.tar.gz` holds the compiled prompts, sea lore and benchmark questions | with `marola-image` |
| `corpus.version` | the marola-corpus release the dataset and Layer 1 read | on its own |
| the devkit (`v0.4.1`) | `flake.nix`'s input, every workflow's `@tag` and `devkit-ref`, `ci.yml`'s two devkit checkouts, `.claude/settings.json`'s marketplace `ref` | all together, in one PR |

## Releases and docs

A `v*` tag makes a GitHub release with `api-docs.tar.gz` (`release.yml`). The API docs readers see
come from the `api-docs` branch, which `api-docs.yml` rewrites on each push to main. The README
and `docs/` are this repo's pages on docs.marola.dev; `docs/benchmarks/` stays off the site, and
links to it become GitHub links.
