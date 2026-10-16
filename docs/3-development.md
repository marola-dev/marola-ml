# Development

How this repo is built, checked, run and published. How every marola repo reviews, tests and
ships is the umbrella's [dev flow](https://docs.marola.dev/3-Ways-of-working/DEV-FLOW/) and
[CI/CD](https://docs.marola.dev/3-Ways-of-working/CI-CD/); this page is what differs here. Each
job has its own page: [the prompt compile](3-development_prompt-compile.md),
[the fine-tune](3-development_finetune.md), [the benchmark gate](3-development_benchmark-gate.md),
[external evaluation](3-development_external-eval.md).

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

No workflow runs on a self-hosted runner since 14 October 2026, when `marola-gpt-publish.yml`
replaced `marola-sea-publish.yml`. A public repo's self-hosted runner runs whatever a pull request
asks it to, so `workflow-runners` (in `ci.yml`'s `runners` job and in `just quality`) fails when
any workflow names `self-hosted`. The devkit's recipes for a runner (`just runner-preflight`,
`just runners`, `just runner-up`) stay for the day a GPU publish needs one again.

## CI

| Workflow | Runs on | Does |
|---|---|---|
| `ci.yml` | every PR, push to main | the devkit's static-ci (actionlint, hadolint, shellcheck, docs-lint), python-ci (ruff and every `--self-test`), the runner guard, agents-check, and the `api-docs` job (`just api-docs` as a check; on main, the output goes to the `api-docs` branch) |
| `docker-local.yml` | push to main touching the model, the pins or the gate; dispatch | build `Dockerfile.local`, benchmark it, move `:local` if the gate passes ([gate](3-development_benchmark-gate.md)) |
| `compile-prompt.yml` | dispatch | compile on an Ollama model inside the job, open a PR in marola-app |
| `marola-gpt-publish.yml` | a pushed `marola-gpt-v*` tag on main (`just sea-release`); dispatch | marola-gpt: the corpus, a LoRA on Tucano-2b4 trained on a GitHub-hosted CPU, the release, the upload to `h0ffmann/marola-gpt` (a dry run by hand; no artifact kept) ([publishing](#publishing-marola-gpt)) |
| `notify-umbrella.yml` | push to main | ask the umbrella to move its pointer, and to rebuild docs.marola.dev when `README.md` or `docs/` changed |
| `pr.yml`, `labels.yml` | PR events; dispatch | the PR body from its commits; the devkit's label set |

`ci.yml`'s static job clones the devkit at `v0.4.1` to run docs-lint, which static-ci has no input
for yet.

## Secrets

| Secret | Used by | For |
|---|---|---|
| `HF_TOKEN` | `marola-gpt-publish.yml` | a fine-grained Hugging Face token with write access to the model repo (`h0ffmann/marola-gpt` for marola-gpt); not set yet |
| `PR_BOT_KEY` (with variable `PR_BOT_APP_ID`) | `compile-prompt.yml`, `notify-umbrella.yml` | the PR in marola-app, opened as marola-pr-bot, and the umbrella dispatch (MIP-0086) |
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
| `just benchmark`, `just finetune-train preset=tiny` | local compute, minutes | anyone, an agent included |
| `just marola-gpt-prepare`, `-train`, `-sample`, `-package`; `just marola-gpt-publish` without `--yes` | local compute, minutes; nothing leaves the machine | anyone, an agent included |
| `just finetune-publish` | an upload that cannot be taken back | a person, by hand |
| `just sea-release` (its tag publishes), `marola-gpt-publish.yml` with dry_run off, `just marola-gpt-publish <v> --yes` | an upload that cannot be taken back | a person, by hand |

An agent dispatches no workflow and creates no tag or release: `.claude/settings.json` denies
`gh workflow run`, `gh release` and `git tag`.

## Publishing marola-gpt

`marola-gpt-publish.yml` is marola-ml's one publish workflow, and a merge never starts it. The
pattern that publishes is a tag `marola-gpt-vX.Y.Z` on a commit of main: `just sea-release`
(`scripts/sea-release.sh`) increments the highest such tag, checks that main is clean, level and
green in CI, and pushes it; the workflow takes its version from the tag, refuses a tag that is not
on main, and uploads. By hand it takes a version (`X.Y.Z`), the number of LoRA training steps, and
`dry_run` (on by default). Either way, on a GitHub-hosted runner it fetches the pinned corpus,
downloads TucanoBR/Tucano-2b4 at the revision `sea/finetune_tucano.py` pins, trains a LoRA adapter
on it on the CPU ([ADR 0004](adr/0004-marola-gpt-sobre-tucano.md)), writes the release directory
(`sea/package.py`) and, on a tag or with `dry_run` off, with the `HF_TOKEN` secret set, uploads it
to `h0ffmann/marola-gpt` as one commit tagged `v<version>` (`sea/publish_hf.py`, which creates the
repository public; the weights carry Tucano-2b4's Apache-2.0). Versions 0.0.x were nanoGPT's, and
both the workflow and `just sea-release` refuse them. It keeps no artifact. Locally the same chain is
`just marola-gpt <version>`, and `just marola-gpt-publish <version> --yes` uploads.

The Llama path's former publish, `marola-sea-publish.yml` (SFT and DPO on the self-hosted runner,
GGUFs to `<owner>/marola-sea-<preset>-GGUF`, tags `marola-sea-v<N>`), was removed on 14 October
2026. Its models already on Hugging Face stay there, and `just marola-sea-pull` still pulls them;
`just finetune-publish` still uploads a GGUF by hand
([the fine-tune page](3-development_finetune.md#publishing-to-hugging-face-mip-0025-51-mip-0033-53)).

## Pins

| Pin | Is | Bump |
|---|---|---|
| `marola-image` | the app image, tag and digest, whose `--benchmark` is the benchmark | with `resources.version`, in one PR: the gate fails a run whose question ids differ from the pinned set ([gate](3-development_benchmark-gate.md#bumping-the-pins)) |
| `resources.version` | the app release whose `ml-resources-<tag>.tar.gz` holds the compiled prompts, sea lore and benchmark questions | with `marola-image` |
| `corpus.version` | the marola-corpus release the dataset and Layer 1 read | on its own |
| the devkit (`v0.4.1`) | `flake.nix`'s input, every workflow's `@tag` and `devkit-ref`, `ci.yml`'s two devkit checkouts, `.claude/settings.json`'s marketplace `ref` | all together, in one PR |

## API docs

The API docs readers see come from the `api-docs` branch, which `ci.yml`'s `api-docs` job rewrites on each
push to main. The README and `docs/` are this repo's pages on docs.marola.dev; `docs/benchmarks/`
stays off the site, and links to it become GitHub links.
