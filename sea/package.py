"""package: one marola-gpt release, ready to publish, from a trained LoRA adapter.

    python3 sea/package.py --version 0.1.0 [--adapter sea/out-marola-gpt]
    python3 sea/package.py --self-test

Writes sea/release/marola-gpt-<version>/:
  adapter_config.json, adapter_model.safetensors   the LoRA adapter (sea/finetune_tucano.py)
  LICENSE      Apache-2.0, Tucano-2b4's own (sea/LICENSE-Tucano-2b4), which the weights carry
  README.md    the model card: the base, how it was changed, its numbers, its licence, credits
  CHECKSUMS    sha256 of every other file, sha256sum's format
The provenance it states is read, never typed: the base and its revision, the training numbers
(the adapter's train_state.json), the corpus version (corpus.version) and this repository's commit.
Standard library only.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEA = ROOT / "sea"
ADAPTER = SEA / "out-marola-gpt"
LICENCE = SEA / "LICENSE-Tucano-2b4"
NAME = "marola-gpt"
WEIGHTS = ("adapter_config.json", "adapter_model.safetensors")


def repo_commit() -> str:
    r = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True
    )
    return r.stdout.strip() or "unknown"


def card(version: str, f: dict) -> str:
    return f"""---
license: apache-2.0
language: [pt]
base_model: {f["base"]}
library_name: peft
tags: [marola, lora, tucano, portuguese, educational]
---

# {NAME} {version}

marola's small language model: a LoRA adapter on [{f["base"]}](https://huggingface.co/{f["base"]})
(revision `{f["base_revision"][:12]}`), trained on marola's corpus of sourced ocean and
marine-safety notes. It continues text, mostly in Portuguese; it is not an assistant, and its text
is not advice about the sea.

| | |
|---|---|
| Base | {f["base"]} at `{f["base_revision"]}` (Apache-2.0), unchanged |
| Change | LoRA r={f["lora"]["r"]}, alpha={f["lora"]["lora_alpha"]} on {", ".join(f["lora"]["target_modules"])}: {f["trainable_params"]:,} trainable parameters |
| Training data | marola-corpus {f["corpus"]}: {f["tokens"]:,} tokens, blocks of {f["block"]} |
| Trained | {f["steps"]} steps on {"a GPU" if f.get("device") == "cuda" else "a CPU"}; best validation loss {f["best_val_loss"]:.4f} at step {f["best_step"]} |
| Code | marola-dev/marola-ml at `{f["repo_commit"]}` (`sea/finetune_tucano.py`) |

## Use it

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained("{f["base"]}", revision="{f["base_revision"]}")
base = AutoModelForCausalLM.from_pretrained("{f["base"]}", revision="{f["base_revision"]}")
model = PeftModel.from_pretrained(base, "h0ffmann/marola-gpt", revision="v{version}")
```

Or, in a checkout of marola-dev/marola-ml: `just marola-gpt-ask "A água-viva" --version {version}`.

## Licence

Apache License 2.0 (`LICENSE`), the licence of Tucano-2b4, Copyright Nicholas Kluge Corrêa, Aniket
Sen, Sophia Falk and Shiza Fatimah. **Modified by marola.dev:** this repository holds only a LoRA
adapter trained by marola on its own corpus; the base weights are not redistributed here and are
downloaded from {f["base"]} unchanged. The code that trained it is MIT (marola-dev/marola-ml).

## Credits

Nicholas Kluge Corrêa, Aniket Sen, Sophia Falk and Shiza Fatimah, for Tucano
([doi:10.1016/j.patter.2025.101325](https://doi.org/10.1016/j.patter.2025.101325)).
Andrej Karpathy, for nanoGPT, which marola-gpt 0.0.x was trained with.
"""


def checksums(files: list[Path]) -> str:
    return "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(files)
    )


def write(out: Path, version: str, adapter: Path, facts: dict, licence: Path) -> list[Path]:
    missing = [n for n in WEIGHTS if not (adapter / n).exists()]
    if missing:
        raise SystemExit(f"package: {adapter} has no {', '.join(missing)}: train it first")
    out.mkdir(parents=True, exist_ok=True)
    for n in WEIGHTS:
        shutil.copyfile(adapter / n, out / n)
    shutil.copyfile(licence, out / "LICENSE")
    (out / "README.md").write_text(card(version, facts), encoding="utf-8")
    files = [out / n for n in (*WEIGHTS, "LICENSE", "README.md")]
    (out / "CHECKSUMS").write_text(checksums(files), encoding="utf-8")
    return files + [out / "CHECKSUMS"]


def self_test() -> int:
    fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal fails
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        fails += 0 if cond else 1

    ok(
        LICENCE.read_text(encoding="utf-8").lstrip().startswith("Apache License"),
        "the release carries Tucano's Apache-2.0 licence",
    )
    facts = {
        "base": "TucanoBR/Tucano-2b4",
        "base_revision": "b8def49a1931508a7cedc1f3fd6ff163515b0983",
        "lora": {"r": 8, "lora_alpha": 16, "target_modules": ["q_proj", "v_proj"]},
        "trainable_params": 1597440,
        "tokens": 5005,
        "block": 128,
        "steps": 200,
        "best_step": 150,
        "best_val_loss": 2.5,
        "corpus": "v0.1.0",
        "repo_commit": "abc",
    }
    c = card("0.1.0", facts)
    ok(
        "license: apache-2.0" in c and "base_model: TucanoBR/Tucano-2b4" in c,
        "the card's front matter names the licence and the base",
    )
    ok("Modified by marola.dev" in c, "the card states the change, as Apache-2.0 asks")
    ok(
        "best validation loss 2.5000 at step 150" in c and "marola-corpus v0.1.0" in c,
        "the card's numbers are the training's",
    )
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "ad").mkdir()
        try:
            write(t / "rel", "0.1.0", t / "ad", facts, LICENCE)
            ok(False, "an untrained adapter is refused")
        except SystemExit:
            ok(True, "an untrained adapter is refused")
        for n in WEIGHTS:
            (t / "ad" / n).write_bytes(n.encode())
        files = write(t / "rel", "0.1.0", t / "ad", facts, LICENCE)
        ok(
            sorted(p.name for p in files)
            == sorted([*WEIGHTS, "LICENSE", "README.md", "CHECKSUMS"]),
            "the release has its five files",
        )
        sums = (t / "rel" / "CHECKSUMS").read_text(encoding="utf-8")
        ok(
            hashlib.sha256(b"adapter_model.safetensors").hexdigest() in sums,
            "CHECKSUMS holds each file's sha256",
        )
    print("package self-test: " + ("ok" if not fails else f"{fails} failure(s)"))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--version")
    ap.add_argument("--adapter", type=Path, default=ADAPTER)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.version:
        ap.error("--version X.Y.Z is required")
    facts = json.loads((a.adapter / "train_state.json").read_text(encoding="utf-8"))
    facts["corpus"] = (ROOT / "corpus.version").read_text(encoding="utf-8").strip()
    facts["repo_commit"] = repo_commit()
    out = SEA / "release" / f"{NAME}-{a.version}"
    files = write(out, a.version, a.adapter, facts, LICENCE)
    print(
        f"package: {NAME} {a.version}: LoRA on {facts['base']}, best val loss "
        f"{facts['best_val_loss']:.4f} -> {out} ({len(files)} files)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
