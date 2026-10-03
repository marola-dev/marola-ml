# marola-ml

The offline Python behind [marola](https://github.com/marola-dev/marola): the DSPy step that
compiles the prompts the app replays, the fine-tune that produces marola-sea (MIP-0025, MIP-0048),
and the benchmark gate that decides whether a model is promoted. None of it runs when the app
answers a question.

It is one of the marola repos under the [umbrella](https://github.com/marola-dev/marola)
(MIP-0070), and its history before the split is marola's, filtered to these files.

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

- [`dspy/`](https://github.com/marola-dev/marola-ml/tree/main/dspy): the prompt compile. The
  `compile prompt` workflow runs it on an Ollama model inside the job and opens a PR in the app
  with the two compiled files.
- [`finetune/`](https://github.com/marola-dev/marola-ml/tree/main/finetune): Tier 1 (a Modelfile)
  and Tier 2 (QLoRA SFT + DPO) of marola-sea, with the dataset builders and the Hugging Face
  publish. Its README is the honest status of each tier.
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

## Docs

[docs/3-development_benchmark-gate.md](docs/3-development_benchmark-gate.md) and
[AGENTS.md](https://github.com/marola-dev/marola-ml/blob/main/AGENTS.md).
