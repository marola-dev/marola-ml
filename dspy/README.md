# marola's DSPy compile step

Python, run **offline only** — this never runs in production and marola's Scala/Kyo runtime
never imports Python. It exists to produce two artifacts, both loaded and replayed at request time
by `marola.llm.CompiledPrompt`/`marola.llm.Reviewer` via a plain OpenAI-compatible chat-completions
call, with no Python in the runtime path:

- `core/src/main/resources/recommendation_prompt.json` — the summarizer (turns a `BestHour` into
  a sentence).
- `core/src/main/resources/review_prompt.json` — the reviewer/critic pass that grades the
  summarizer's own output and can replace it (`marola.llm.Reviewer`).

See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §5a for why this exists and
[`compile_recommendation_prompt.py`](./compile_recommendation_prompt.py) for the actual program
(both `dspy.Signature`s, both trainsets, both compile calls) — this file is just the "how to run
it" instructions.

DSPy is Python-only ("**D**eclarative **S**elf-improving **Py**thon" — no JVM port exists — see
[`FUTURE-WORK.md`](../docs/FUTURE-WORK.md) §10 for the Scala-ecosystem gap this leaves and the
proposed `ds4s` port), and its optimizer is a compile-time step, not a runtime dependency, so it
doesn't need to run in the deployed service.

## Why this needs a real LLM, and costs a little money

DSPy's optimizers (`BootstrapFewShot`, `MIPROv2`, ...) work by actually *calling* a language model
repeatedly — running the draft program against training examples, checking outputs against a
metric, and keeping/refining what worked. There's no way to "compile" a prompt without a real model
in the loop. Budget a few cents to a few dollars depending on the optimizer and trainset size
(`BootstrapFewShot` with 3 examples, as configured here, is cheap; `MIPROv2` costs more). Per
`AGENTS.md`'s cost-safety rule: don't run this against a paid endpoint without knowing that going
in — it's a deliberate, small, one-time spend, not something to run repeatedly or in CI.

## Setup

```bash
cd dspy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running it

Point `MAROLA_DSPY_MODEL` (a [LiteLLM](https://docs.litellm.ai/docs/providers) model string,
since that's what DSPy uses under the hood) and the matching provider credentials at whichever
model marola will actually run at request time, so the optimized prompt matches the model
that'll replay it:

```bash
# Azure OpenAI / Foundry — same deployment as FOUNDRY_MODEL_DEPLOYMENT elsewhere in this repo.
# These are LiteLLM's own env var names (https://docs.litellm.ai/docs/providers/azure), not this
# repo's usual FOUNDRY_* ones — DSPy doesn't know about azure-identity/managed-identity, it needs
# a plain API key here.
export AZURE_API_KEY=...
export AZURE_API_BASE=https://<your-resource>.openai.azure.com
export AZURE_API_VERSION=2026-01-01-preview
export MAROLA_DSPY_MODEL=azure/<your-deployment-name>

python compile_recommendation_prompt.py
```

Or, for quick local experimentation before Foundry is provisioned:

```bash
export OPENAI_API_KEY=sk-...
python compile_recommendation_prompt.py   # defaults to openai/gpt-4o-mini
```

Either way this writes both `recommendation_prompt.json` and `review_prompt.json` in one run. Re-run
it whenever `TRAINSET`/`REVIEW_TRAINSET` grow (these double as hand-labeled eval sets — see
`../docs/FUTURE-WORK.md` §4.1 for the gap between "doubles as an eval set" and an actual held-out
`dspy.Evaluate` loop, which doesn't exist yet) or the target model changes — there's no watch mode,
it's a manual step you re-run and commit both resulting JSON files, same as any other compiled
artifact.

## Optional: tracing the compile run with Langfuse

`BootstrapFewShot`/`MIPROv2` call the model many times per run (once per training example per
bootstrap attempt, more for `MIPROv2`'s Bayesian search) to figure out which few-shot demos and
instructions actually work — that process is otherwise a black box. Setting these three env vars
turns on [Langfuse](https://langfuse.com) tracing for the whole run, via the OTEL-based Python SDK
v3 and [Langfuse's own DSPy integration](https://langfuse.com/integrations/frameworks/dspy):

```bash
export MAROLA_LANGFUSE_PUBLIC_KEY=pk-lf-...
export MAROLA_LANGFUSE_SECRET_KEY=sk-lf-...
export MAROLA_LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted instance
python compile_recommendation_prompt.py
```

Get a free key pair at [cloud.langfuse.com](https://cloud.langfuse.com) (generous free tier) or
self-host (`LANGFUSE_BASE_URL` → `http://localhost:3000` per Langfuse's own docs). Omit these three
vars entirely to skip tracing — `_init_langfuse_tracing()` checks for
`MAROLA_LANGFUSE_PUBLIC_KEY` first and no-ops silently if it's unset, and degrades to a warning
(never a crash) if the credentials are set but unreachable/invalid, so a broken Langfuse setup
never blocks the actual compile step.

Uses the `MAROLA_LANGFUSE_*` prefix (this repo's env var convention — see `AppConfig.scala`,
root `.env.example`) rather than Langfuse's own bare `LANGFUSE_*` names directly, so
`_init_langfuse_tracing()` bridges one to the other internally.

## Status

**Both compile steps have actually been run against a real LLM**, end to end, more than once — a
local Ollama model, not a paid API, so this didn't cost anything: `ollama_chat/dolphin-mixtral:8x7b`
(26GB, `MAROLA_DSPY_API_BASE=http://localhost:11434`) and, separately while writing `RUN-LOCALLY.md`,
the much smaller `llama3.2:1b` (1.3GB). Both produced real compiled artifacts with genuine
LLM-bootstrapped demos (each demo carries `"augmented": true`; inspect the JSON directly to see
this). Along the way this also surfaced and fixed a real, unrelated environment issue: `tokenizers`'
Rust extension needs `libstdc++.so.6`, which a Nix-based Python environment doesn't put on the
default linker path —

```bash
export LD_LIBRARY_PATH="$(ls -d /nix/store/*-gcc-*-lib 2>/dev/null | sort -V | tail -1)/lib:$LD_LIBRARY_PATH"
```

(picks the newest `gcc-*-lib` derivation on your store if more than one is present — verified this
resolves correctly on the machine this was written on, which had both a 15.2.0 and 15.3.0 copy)
needed once per shell before running `python compile_recommendation_prompt.py`, or DSPy fails with
`ImportError: libstdc++.so.6: cannot open shared object file`.

The Scala-side loader (`marola.llm.CompiledPrompt`, `marola.llm.Reviewer`) exists and was run live
against both compiled artifacts (`just run -- --summarize`) — see `../docs/ARCHITECTURE.md` §5a's
own Status notes for the full detail, including one case where the reviewer correctly caught a
deliberately-planted flaw in a draft summary.

`langfuse==4.15.1` + `openinference-instrumentation-dspy` are confirmed importable and the
graceful-degradation path (credentials set, endpoint unreachable) was exercised directly, but the
actual Langfuse happy path (a trace landing in a real project) remains unverified — no Langfuse
account was set up in this environment. `AzureFoundryLlmClient`'s live path is similarly unverified
— no Foundry project provisioned (`AGENTS.md`'s cost-safety rule).
