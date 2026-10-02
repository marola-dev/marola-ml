# marola-ml

marola's offline Python (MIP-0070 §5.2): the DSPy prompt compile (the app's ARCHITECTURE §5a), the
marola-sea fine-tune (MIP-0025, MIP-0048) and the benchmark gate (MIP-0008 §5.3).

## The contracts

| Piece | Where |
|---|---|
| The app image the benchmark runs | `marola-image`, read by [`scripts/app-image.sh`](https://github.com/marola-dev/marola-ml/blob/main/scripts/app-image.sh) |
| The app's resources (compiled prompts, sea lore, the question set) | `ml-resources-<tag>.tar.gz` on the marola-app release `resources.version` names, unpacked by [`scripts/resources-fetch.sh`](https://github.com/marola-dev/marola-ml/blob/main/scripts/resources-fetch.sh) |
| The corpus | `marola-corpus-<tag>.tar.gz`, pinned in `corpus.version` |
| The compiled prompts, back to the app | a PR from [`compile-prompt.yml`](https://github.com/marola-dev/marola-ml/blob/main/.github/workflows/compile-prompt.yml) |
| The kept benchmark runs | [`docs/benchmarks/`](https://github.com/marola-dev/marola-ml/tree/main/docs/benchmarks) (on GitHub: the docs site leaves `benchmarks/` out as repo artefacts) |
| The API docs | `api-docs.tar.gz` on each `v*` release, served at docs.marola.dev under `repos/marola-ml/api/` |

## The gate

`docker-local.yml` builds `Dockerfile.local`, starts it, runs the pinned app image's `--benchmark`
against it (`scripts/benchmark.sh`, which fails when the app reports a failure or saves no report)
and checks the report with `scripts/benchmark_gate.py`:

- `rag-general` coverage (all) at most 0.05 below the best kept run, and above the plain prompt's;
- every question id in the pinned `benchmark_questions.json` answered on all three arms, so an
  image and a resources pin that drifted apart fail.

Only then does `ghcr.io/marola-dev/marola-ml:local` move to the new build. The run embeds with
`nomic-embed-text:v1.5`, which the image also carries: Ollama serves `/api/embed` only for a model
whose GGUF declares a pooling type, so the kept runs' `llama3.2` embeddings now answer HTTP 501.

The gate does not know the embedder changed: it compares against the best `rag-general` in the
newest kept file (`2026-09-05.md`, 0.84, measured with `llama3.2` embeddings), and the first run on
`nomic-embed-text` may pass or fail on that alone.

**After a deliberate model or embedder change that fails the gate**, the intended process is a new
reference, not a wider tolerance: take the run's report from its `benchmark-<run_id>` artifact
(uploaded even when the gate fails), commit it as `docs/benchmarks/<date>.md` with a line saying
what changed (model, embedder), and merge it in a PR. The gate reads the newest file by name, so
the next run compares against it. A dispatch with a larger `tolerance` is for a one-off promotion
you have reviewed by hand, and leaves the reference where it was.

## Bumping the app

Change `marola-image` (tag and digest) and `resources.version` in one PR. `docker-local.yml` runs
on it after merge; a `workflow_dispatch` of it on the branch tries the pin first.
