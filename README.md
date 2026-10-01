# marola-ml

The offline Python behind [marola](https://github.com/marola-dev/marola): the DSPy step that
compiles the prompts the app replays, the fine-tune that produces marola-sea, and the benchmark
gate that decides whether a model is promoted. None of it runs when the app answers a question.

It is one of the marola repos under the [umbrella](https://github.com/marola-dev/marola)
(MIP-0070), and its history before the split is marola's, filtered to these files.

## What is here

- [`dspy/`](https://github.com/marola-dev/marola-ml/tree/main/dspy): the prompt compile. The
  `compile prompt` workflow runs it on an Ollama model inside the job and opens a PR in the app
  with the two compiled files.
- [`finetune/`](https://github.com/marola-dev/marola-ml/tree/main/finetune): Tier 1 (a Modelfile)
  and Tier 2 (QLoRA SFT + DPO) of marola-sea, with the dataset builders and the Hugging Face
  publish. Its README is the honest status of each tier.
- [`docs/benchmarks/`](https://github.com/marola-dev/marola-ml/blob/main/docs/benchmarks/2026-09-05.md): the kept benchmark runs.
  `scripts/benchmark_gate.py` fails a new run that falls more than 0.05 below the best of them, or
  below the plain prompt. After a deliberate model or embedder change, a failing run's report is
  committed as the new reference ([docs/](docs/index.md) says how).
- `Dockerfile.local`: Ollama with `marola-llama3.2` already in its store, published as
  `ghcr.io/marola-dev/marola-ml:local` once it clears the gate (`docker-local.yml`).
- `marola-sea-publish.yml`: train and publish marola-sea, by hand only. It waits on two things,
  each tracked in its own issue: the HF_TOKEN secret; the marola-sea runners registered at org
  level for this repo. marola already has the tag `marola-sea-v1`, which this repo's history does
  not carry: dispatch the first publish with `major_version: 2`.

## What it reads from other repos

Pinned releases, never another repo's tree: the app image (`marola-image`), the app's resources
tarball (`resources.version`) and the corpus (`corpus.version`). `just corpus-fetch` and
`just resources-fetch` unpack the last two into `.tmp/`.

```bash
nix develop
just quality            # every gate CI runs
just finetune-dataset   # the training set, from the pinned resources and corpus
just benchmark          # the pinned app image's --benchmark on your Ollama, then the gate
```

More in [docs/](docs/index.md) and [AGENTS.md](https://github.com/marola-dev/marola-ml/blob/main/AGENTS.md).
