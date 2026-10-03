# The benchmark gate

`docker-local.yml` builds `Dockerfile.local` (Ollama with `marola-llama3.2` and the benchmark's
embedder, `nomic-embed-text:v1.5`, already in its store), starts it, runs the pinned app image's
`--benchmark` against it (`scripts/benchmark.sh`, which fails when the app reports a failure or
saves no report), and checks the report with `scripts/benchmark_gate.py`:

- `rag-general` coverage (all) at most 0.05 below the best kept run, and above the plain prompt's;
- every question id in the pinned `benchmark_questions.json` answered on all three arms, so an
  image and a resources pin that drifted apart fail.

Only then does `ghcr.io/marola-dev/marola-ml:local` move to the new build.

## The embedder gap

The run embeds with `nomic-embed-text:v1.5`, which the image also carries: Ollama serves
`/api/embed` only for a model whose GGUF declares a pooling type, so the kept runs' `llama3.2`
embeddings now answer HTTP 501. The gate does not know the embedder changed: it compares against
the best `rag-general` in the newest kept file (`2026-09-05.md`, 0.84, measured with `llama3.2`
embeddings), and the first run on `nomic-embed-text` may pass or fail on that alone.

## Re-baselining

**After a deliberate model or embedder change that fails the gate**, the intended process is a new
reference, not a wider tolerance: take the run's report from its `benchmark-<run_id>` artifact
(uploaded even when the gate fails), commit it as `docs/benchmarks/<date>.md` with a line saying
what changed (model, embedder), and merge it in a PR. The gate reads the newest file by name, so
the next run compares against it. A dispatch with a larger `tolerance` is for a one-off promotion
you have reviewed by hand, and leaves the reference where it was.

## Bumping the pins

Change `marola-image` (tag and digest) and `resources.version` together, in one PR: the gate fails
a run whose question ids differ from the pinned question set. `docker-local.yml` runs on it after
merge; a `workflow_dispatch` of it on the branch tries the pin first.
