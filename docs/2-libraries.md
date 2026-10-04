# Libraries

Python 3.12 (`ruff.toml`'s `target-version`, CI's `setup-python`). Everything outside `dspy/` and
the training scripts' lazy imports is the standard library, so the gates need no `pip install`.
The two `requirements.txt` files pin loosely, with a floor and sometimes a major-version ceiling:
DSPy, Langfuse and the training stack move fast, and the files say to re-check before trusting a
pin long-term.

## The prompt compile (`dspy/requirements.txt`)

| Library | Version | Why | Alternatives |
|---|---|---|---|
| DSPy | `>=3.3.1,<4` | Compiles the summarizer and reviewer prompts with `BootstrapFewShot` | Python-only, no JVM port; FUTURE-WORK §10 proposes `ds4s` ([the compile](3-development_prompt-compile.md)) |
| Langfuse | `>=4.15.6,<5` | Optional tracing of every LLM call in a compile, when `MAROLA_LANGFUSE_PUBLIC_KEY` is set | — |
| openinference-instrumentation-dspy | unpinned | Langfuse's DSPy integration | — |
| MLflow | `>=3.16.1,<4` | Optional: one run per compile, when `MAROLA_MLFLOW_TRACKING_URI` is set (MIP-0010) | `mlflow.dspy.autolog()`, rejected: no aggregate metric, wrong artifact names |

All three tracing packages install unconditionally; tracing is opted into at run time.

## The fine-tune (`finetune/requirements.txt`)

| Library | Version | Why |
|---|---|---|
| torch | `>=2.14.0` | Training. CUDA torch comes from a venv (`just ml-venv`), not nixpkgs |
| transformers | `>=5.17.0` | The base models and tokenizers, and 4-bit loading |
| peft | `>=0.21.0` | The LoRA adapter, and the merge into the base |
| trl | `>=1.13.0` | `SFTTrainer` for the adapter, `DPOTrainer` for Layer 3 |
| datasets | `>=5.0.1` | Loading the JSONL sets |
| accelerate | `>=1.15.0` | `--device hybrid`'s `max_memory` spill into CPU RAM |
| bitsandbytes | `>=0.50.2`, Linux only | 4-bit QLoRA on CUDA; on CPU, omit it and pass `--no-4bit` |
| huggingface_hub | `>=2.0.0` | `publish_hf.py`'s upload |
| gguf, sentencepiece, protobuf | `>=0.19.0`, `>=0.2.2`, `>=7.36.2` | llama.cpp's `convert_hf_to_gguf.py`, which `merge_export.py` shells out to; sentencepiece even for a model without its tokenizer (the file's comment says why) |

llama.cpp itself is not a Python dependency: `merge_export.py --llama-cpp <dir>` takes a checkout,
and `marola-sea-publish.yml` uses nixpkgs' `llama-cpp` source.

## Models and serving

| What | Version | Where it is pinned |
|---|---|---|
| Ollama | `ollama/ollama:0.33.3` | `Dockerfile.local`, `compile-prompt.yml`'s service; `nix develop` has nixpkgs' `ollama` |
| `llama3.2` | Ollama's tag | Tier 1's `FROM` (`finetune/Modelfile`) |
| `nomic-embed-text:v1.5` | Ollama's tag | `Dockerfile.local`, the benchmark's embedder: `llama3.2` has no pooling type, so Ollama answers its `/api/embed` with a 501 |
| Training bases | per preset | `PRESETS` in `finetune/train_lora.py`; the [fine-tune page](3-development_finetune.md#presets-and-what-each-costs-on-your-machine) has the table and licences |

## Tools

| Tool | Version | Where |
|---|---|---|
| marola-devkit | `v0.4.1` | `flake.nix`'s input, every reusable workflow's `@tag` and `devkit-ref`, `.claude/settings.json`'s marketplace `ref`: bumped together |
| ruff | `0.16.5` in CI | `ci.yml`'s `python` job; `ruff.toml` |
| hadolint | `2.14.0` in CI | `ci.yml`'s `static` job, on `Dockerfile.local` |
| shellcheck, actionlint | the devkit's static-ci defaults | `ci.yml`'s `static` job |
| docs-lint | the devkit's, `v0.4.1` | `just quality`, and `ci.yml`'s `static` job |
| pdoc | `16.0.0` in `release.yml`; nixpkgs' in `nix develop` | `just api-docs` |
| CUDA venv helpers | `labs/cuda` flake input (`setup-ml-venv`, `setup-cuda-cache`, `python-cuda`) | `flake.nix`, x86_64-linux only |

Locally, `nix develop` provides the lint tools and the devkit's tools at the flake's versions. The
repo tracks no `flake.lock`, so `nixpkgs` and the `cuda` input resolve when the shell is first
built.
