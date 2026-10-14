"""package: one marolaGPT release, ready to publish, from a trained checkpoint.

    python3 sea/package.py --version 0.1.0 [--ckpt sea/nanogpt/out-marolagpt/ckpt.pt]
    python3 sea/package.py --self-test

Writes sea/release/marolaGPT-<version>/:
  model.pt     the weights, the model's shape and its dataset's name, no optimizer state
  meta.pkl     the character vocabulary (sea/nanogpt/data/marola_corpus/meta.pkl)
  LICENSE      marola-ml's licence, which restricts the model's distribution (../../LICENSE)
  README.md    the model card: what it is, how it was made, its numbers, its licence
  CHECKSUMS    sha256 of every other file, sha256sum's format
The provenance it states is read, never typed: the corpus version (corpus.version), the nanoGPT
commit (sea/FORK.tsv), this repository's commit, and the iteration and validation loss the
checkpoint holds. torch is needed to read the checkpoint, not for the self-test.
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEA = ROOT / "sea"
CKPT = SEA / "nanogpt" / "out-marolagpt" / "ckpt.pt"
META = SEA / "nanogpt" / "data" / "marola_corpus" / "meta.pkl"
NAME = "marolaGPT"
HF_REPO = "h0ffmann/marolaGPT"


def nanogpt_commit(fork_tsv: Path) -> str:
    for line in fork_tsv.read_text(encoding="utf-8").splitlines():
        if line.startswith("# Forked on ") and " at commit " in line:
            return line.split(" at commit ")[1].split()[0]
    raise SystemExit(f"package: no 'at commit' line in {fork_tsv}")


def repo_commit() -> str:
    r = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True
    )
    return r.stdout.strip() or "unknown"


def card(version: str, facts: dict) -> str:
    return f"""---
license: other
license_name: marola-ml-restricted
license_link: LICENSE
tags: [marola, nanogpt, character-level, small-language-model, educational]
---

# {NAME} {version}

A small language model that marola trains from random weights on its own corpus of sourced ocean
and marine-safety notes. An educational model: it shows how a GPT learns a small domain from
scratch. It is not an assistant, and its text is not advice about the sea.

| | |
|---|---|
| Architecture | nanoGPT (Andrej Karpathy, MIT), character level: {facts["n_layer"]} layers, {facts["n_head"]} heads, width {facts["n_embd"]}, context {facts["block_size"]} |
| Parameters | {facts["params"]:,} |
| Vocabulary | {facts["vocab_size"]} characters |
| Training data | marola-corpus {facts["corpus"]} |
| Trained | {facts["iter_num"]} iterations; best validation loss {facts["best_val_loss"]:.4f} |
| Code | marola-dev/marola-ml at `{facts["repo_commit"]}`; nanoGPT at `{facts["nanogpt"][:12]}` |

## Use it

Inside a checkout of marola-dev/marola-ml: put `model.pt` at `sea/nanogpt/out-marolagpt/ckpt.pt`
and `meta.pkl` at `sea/nanogpt/data/marola_corpus/meta.pkl`, then `just marolagpt-sample`.

## Licence

Restricted: see `LICENSE`. {NAME} may be used by marola's contributors. It may not be
redistributed outside marola-dev's own channels: this repository is one of them while the owner
keeps it as the official one. The code it was trained with that came from nanoGPT stays under
nanoGPT's MIT License (Copyright (c) 2022 Andrej Karpathy).

## Credits

Andrej Karpathy, for nanoGPT. Fabio Akita, whose microgpt gave marola the idea of a GPT trained
from scratch on one machine.
"""


def checksums(files: list[Path]) -> str:
    return "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(files)
    )


def facts_from(ckpt: dict, corpus: str, nanogpt: str, commit: str) -> dict:
    args = ckpt["model_args"]
    params = sum(t.numel() for k, t in ckpt["model"].items() if not k.endswith("attn.bias"))
    return {
        "n_layer": args["n_layer"],
        "n_head": args["n_head"],
        "n_embd": args["n_embd"],
        "block_size": args["block_size"],
        "vocab_size": args["vocab_size"],
        "params": params,
        "iter_num": ckpt.get("iter_num", 0),
        "best_val_loss": float(ckpt.get("best_val_loss", float("nan"))),
        "corpus": corpus,
        "nanogpt": nanogpt,
        "repo_commit": commit,
    }


def write(
    out: Path, version: str, weights: dict, facts: dict, meta: Path, licence: Path, save
) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    save(weights, out / "model.pt")
    shutil.copyfile(meta, out / "meta.pkl")
    shutil.copyfile(licence, out / "LICENSE")
    (out / "README.md").write_text(card(version, facts), encoding="utf-8")
    files = [out / n for n in ("model.pt", "meta.pkl", "LICENSE", "README.md")]
    (out / "CHECKSUMS").write_text(checksums(files), encoding="utf-8")
    return files + [out / "CHECKSUMS"]


def self_test() -> int:
    fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal fails
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        fails += 0 if cond else 1

    ok(
        nanogpt_commit(SEA / "FORK.tsv").startswith("3adf61e154c3"),
        "the nanoGPT commit is read from FORK.tsv",
    )

    class T:  # a stand-in for a tensor: only numel() is read
        def __init__(self, n: int) -> None:
            self.n = n

        def numel(self) -> int:
            return self.n

    ckpt = {
        "model": {"w": T(100), "h.0.attn.bias": T(9)},
        "model_args": {
            "n_layer": 4,
            "n_head": 4,
            "n_embd": 128,
            "block_size": 128,
            "vocab_size": 87,
        },
        "iter_num": 600,
        "best_val_loss": 2.4854,
    }
    f = facts_from(ckpt, "v0.1.0", "3adf61e154c3fe", "abc")
    ok(f["params"] == 100, "the causal-mask buffers are not counted as parameters")
    c = card("0.1.0", f)
    ok("license: other" in c and "Restricted" in c, "the card states the restricted licence")
    ok(
        "best validation loss 2.4854" in c and "marola-corpus v0.1.0" in c,
        "the card's numbers are the checkpoint's",
    )
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "meta.pkl").write_bytes(b"m")
        (t / "LICENSE").write_text("restricted\n", encoding="utf-8")
        files = write(
            t / "rel",
            "0.1.0",
            {"model": {}},
            f,
            t / "meta.pkl",
            t / "LICENSE",
            lambda obj, p: p.write_bytes(b"weights"),
        )
        names = sorted(p.name for p in files)
        ok(
            names == ["CHECKSUMS", "LICENSE", "README.md", "meta.pkl", "model.pt"],
            "the release has its five files",
        )
        sums = (t / "rel" / "CHECKSUMS").read_text(encoding="utf-8")
        ok(
            hashlib.sha256(b"weights").hexdigest() + "  model.pt" in sums,
            "CHECKSUMS holds each file's sha256",
        )
    print("package self-test: " + ("ok" if not fails else f"{fails} failure(s)"))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--version")
    ap.add_argument("--ckpt", type=Path, default=CKPT)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.version:
        ap.error("--version X.Y.Z is required")
    import torch

    ckpt = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    corpus = (ROOT / "corpus.version").read_text(encoding="utf-8").strip()
    facts = facts_from(ckpt, corpus, nanogpt_commit(SEA / "FORK.tsv"), repo_commit())
    out = SEA / "release" / f"{NAME}-{a.version}"
    # sample.py finds the vocabulary through config["dataset"], so that one key is kept.
    weights = {
        "model": ckpt["model"],
        "model_args": ckpt["model_args"],
        "config": {"dataset": ckpt["config"]["dataset"]},
        "iter_num": facts["iter_num"],
        "best_val_loss": facts["best_val_loss"],
    }
    files = write(out, a.version, weights, facts, META, ROOT / "LICENSE", torch.save)
    print(
        f"package: {NAME} {a.version}: {facts['params']:,} parameters, best val loss "
        f"{facts['best_val_loss']:.4f} -> {out} ({len(files)} files)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
