set shell := ["bash", "-euo", "pipefail", "-c"]
set allow-duplicate-recipes

# The devkit's shared recipes (uprd, pr, stack, issue-*, ...), from the tree `nix develop` links.
import? '.devkit/devkit.just'

default:
    @just --list

# Unpack the marola-corpus release pinned in corpus.version into .tmp/knowledge.
corpus-fetch:
    scripts/corpus-fetch.sh

# Unpack the app's resources tarball pinned in resources.version into .tmp/resources.
resources-fetch:
    scripts/resources-fetch.sh

# Tier 2 prep: chat-format JSONL from the DSPy demos, sea lore and the corpus.
finetune-dataset: corpus-fetch resources-fetch
    python3 finetune/build_dataset.py

# Layer 3: DPO preference pairs from the reviewer's reject/revise demos. MIP-0025 §4.3.
finetune-dpo-dataset: resources-fetch
    python3 finetune/build_dpo_dataset.py

# Tier 1: llama3.2 plus marola's persona/decoding as an Ollama model (finetune/Modelfile).
finetune-model base="llama3.2":
    mkdir -p .tmp && sed 's/^FROM .*/FROM {{ base }}/' finetune/Modelfile > .tmp/Modelfile && ollama create marola-llama3.2 -f .tmp/Modelfile

# Tier 2: a trained adapter on its own base, as the Ollama model `marola-sea-<preset>`.
finetune-adapter-model preset="tiny":
    #!/usr/bin/env bash
    set -euo pipefail
    from="$(python3 -c "import sys; sys.path.insert(0, 'finetune'); from train_lora import PRESETS; print(PRESETS['{{ preset }}']['ollama'])")"
    gguf="$PWD/finetune/out/{{ preset }}/adapter.gguf"
    [ -f "$gguf" ] || { echo "no adapter GGUF at $gguf — train it, then convert with llama.cpp's convert_lora_to_gguf.py" >&2; exit 1; }
    mkdir -p .tmp
    sed -e "s|^FROM .*|FROM $from|" -e "s|^ADAPTER .*|ADAPTER $gguf|" finetune/Modelfile.adapter > .tmp/Modelfile.adapter
    ollama create marola-sea-{{ preset }} -f .tmp/Modelfile.adapter

# Tier 2: QLoRA adapter. preset=tiny trains on CPU in minutes; small|base need more.
finetune-train preset="tiny" *args="":
    python3 finetune/train_lora.py --preset {{ preset }} {{ args }}

# Layer 3 training: DPO on top of an existing SFT adapter (`just finetune-train` first).
finetune-train-dpo preset="tiny" *args="":
    python3 finetune/train_dpo.py --preset {{ preset }} {{ args }}

# VRAM, RAM, disk and a rough ETA for a fine-tune on this machine, before starting it. MIP-0048.
finetune-preflight preset="tiny" *args="":
    python3 finetune/preflight.py --preset {{ preset }} {{ args }}

# Merge a LoRA adapter into its base and export GGUFs. MIP-0025 §5.1.
finetune-merge preset="tiny" llama_cpp="" *args="":
    python3 finetune/merge_export.py --preset {{ preset }} {{ if llama_cpp != "" { "--llama-cpp " + llama_cpp } else { "--dry-run" } }} {{ args }}

# Publish a trained .gguf to a Hugging Face model repo (MIP-0025 §5.1).
finetune-publish repo gguf base *args:
    python3 finetune/publish_hf.py --repo {{ repo }} --gguf {{ gguf }} --base-model {{ base }} {{ args }}

# Create/update the venv marola-sea trains in — labs/cuda's setup-ml-venv; call its
# bin/python-cuda afterwards, never bin/python.
ml-venv *args:
    REQUIREMENTS=finetune/requirements.txt VENV_ROOT="${VENV_ROOT:-$HOME/.marola-ml-venv}" setup-ml-venv {{ args }}

# One-time host setup: the CUDA binary cache, so torchWithCuda is fetched, not compiled.
gpu-cache-setup *args:
    setup-cuda-cache {{ args }}

# Pull the published marola-sea GGUF from Hugging Face into Ollama as `marola-sea`.
marola-sea-pull preset="tiny" quant="Q4_K_M" owner="":
    scripts/marola-sea-pull.sh {{ preset }} {{ quant }} {{ owner }}

# Analyse a finished training run (HF trainer_state.json); `just training-logs <run-id>` for CI's.
analyze-training *args:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "{{ args }}" ]; then
        python3 scripts/analyze_training.py {{ args }}
    else
        root="${CKPT_ROOT:-../marola-checkpoints}/${PRESET:-tiny}"
        python3 scripts/analyze_training.py "$root/adapter" "$root/dpo-adapter"
    fi

# Download a marola-sea publish run's logs (default: the latest) into .tmp/training-logs/.
training-logs run_id="":
    #!/usr/bin/env bash
    set -euo pipefail
    id="{{ run_id }}"
    [ -n "$id" ] || id="$(gh run list --workflow "marola-sea publish" --limit 1 --json databaseId --jq '.[0].databaseId')"
    mkdir -p .tmp/training-logs
    gh run download "$id" --dir .tmp/training-logs
    echo "training-logs: run $id in .tmp/training-logs — analyse with: just analyze-training .tmp/training-logs/*/"

# The marola-local image (Dockerfile.local: Ollama with marola-llama3.2 in its store).
docker-build-local:
    docker build -f Dockerfile.local -t marola-ml:local .

# The pinned app image's --benchmark against the Ollama on :11434 (with `model` and
# nomic-embed-text:v1.5 pulled), then the gate. Needs docker.
benchmark model="marola-llama3.2": resources-fetch
    MAROLA_LOCAL_LLM_MODEL="{{ model }}" scripts/benchmark.sh
    just benchmark-gate

# The promotion gate on the newest data/benchmark-*.md (docker-local.yml runs the same).
benchmark-gate tolerance="0.05": resources-fetch
    python3 scripts/benchmark_gate.py check --new data --kept docs/benchmarks --questions .tmp/resources/benchmark_questions.json --tolerance {{ tolerance }}

# DSPy compile into .tmp/compiled (an LLM in the loop: see docs/3-development_prompt-compile.md for the cost).
compile-prompt *args:
    python3 dspy/compile_recommendation_prompt.py --out .tmp/compiled {{ args }}

# <out>/python/ pdoc, the devkit's api-docs.yml caller (MIP-0074 §5.2; release.yml's tarball is separate).
api-docs out=".tmp/api-docs":
    scripts/api-docs.sh --dir {{ out }}

# Every gate CI runs.
quality: corpus-fetch resources-fetch
    #!/usr/bin/env bash
    set -euo pipefail
    for tool in ruff shellcheck actionlint hadolint agents-check workflow-runners docs-lint; do command -v "$tool" >/dev/null || { echo "quality: $tool not installed — run inside 'nix develop'" >&2; exit 1; }; done
    just --list >/dev/null
    ruff check .
    ruff format --check .
    shellcheck --severity=error scripts/*.sh
    actionlint
    hadolint Dockerfile.local
    scripts/corpus-fetch.sh --self-test
    scripts/resources-fetch.sh --self-test
    scripts/app-image.sh --self-test
    scripts/benchmark.sh --self-test
    scripts/api-docs.sh --self-test
    scripts/marola-sea-pull.sh --self-test
    python3 scripts/benchmark_gate.py --self-test
    python3 scripts/analyze_training.py --self-test
    python3 finetune/train_lora.py --self-test
    python3 finetune/preflight.py --self-test
    python3 finetune/merge_export.py --self-test
    python3 finetune/build_dataset.py --self-test
    python3 finetune/build_dpo_dataset.py --self-test
    workflow-runners
    agents-check
    docs-lint

# The devkit hooks' contract: fast checks at commit, the full gate at push.
precommit:
    ruff check .
    agents-check

prepush:
    just quality
