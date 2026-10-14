"""prepare_corpus: marola's corpus notes as nanoGPT's character-level dataset, for marola-sea.

    python3 sea/prepare_corpus.py [--corpus DIR] [--out DIR]
    python3 sea/prepare_corpus.py --self-test

Reads every Markdown note of the pinned corpus (`just corpus-fetch` unpacks it into
`.tmp/knowledge`), sorted by path so two runs give the same bytes, joined by a blank line. Writes
what nanoGPT's `train.py` reads for `dataset = 'marola_corpus'` (sea/nanogpt/data/marola_corpus/):
train.bin and val.bin (uint16 character ids, a 90/10 split) and meta.pkl (the vocabulary). The
shape is nanoGPT's data/shakespeare_char/prepare.py; this file is marola's own, not copied.
Standard library and numpy only.
"""

import argparse
import pickle
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / ".tmp" / "knowledge"
OUT = Path(__file__).resolve().parent / "nanogpt" / "data" / "marola_corpus"


def read_corpus(corpus: Path) -> str:
    notes = sorted(p for p in corpus.rglob("*.md") if p.is_file())
    if not notes:
        raise SystemExit(f"prepare_corpus: no .md under {corpus}: run `just corpus-fetch` first")
    return "\n\n".join(p.read_text(encoding="utf-8").strip() for p in notes) + "\n"


def encode(text: str) -> tuple[list[int], dict]:
    chars = sorted(set(text))
    if len(chars) > 65535:
        raise SystemExit("prepare_corpus: more than 65 535 distinct characters do not fit uint16")
    stoi = {ch: i for i, ch in enumerate(chars)}
    itos = {i: ch for i, ch in enumerate(chars)}
    return [stoi[c] for c in text], {"vocab_size": len(chars), "itos": itos, "stoi": stoi}


def write(corpus: Path, out: Path) -> dict:
    import numpy as np

    text = read_corpus(corpus)
    ids, meta = encode(text)
    cut = int(len(ids) * 0.9)
    out.mkdir(parents=True, exist_ok=True)
    np.array(ids[:cut], dtype=np.uint16).tofile(out / "train.bin")
    np.array(ids[cut:], dtype=np.uint16).tofile(out / "val.bin")
    with open(out / "meta.pkl", "wb") as f:
        pickle.dump(meta, f)
    return {"chars": len(text), "vocab": meta["vocab_size"], "train": cut, "val": len(ids) - cut}


def self_test() -> int:
    fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal fails
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        fails += 0 if cond else 1

    with tempfile.TemporaryDirectory() as tmp:
        corpus = Path(tmp) / "knowledge"
        (corpus / "safety").mkdir(parents=True)
        (corpus / "b.md").write_text("# Ondas\nSource: x\n\nmar\n", encoding="utf-8")
        (corpus / "safety" / "a.md").write_text("# Água-viva\n", encoding="utf-8")
        (corpus / "skip.txt").write_text("not a note", encoding="utf-8")
        text = read_corpus(corpus)
        ok(
            text == "# Ondas\nSource: x\n\nmar\n\n# Água-viva\n",
            "notes sorted by path, joined by a blank line",
        )
        ok("not a note" not in text, "only .md files are read")
        ids, meta = encode(text)
        ok("".join(meta["itos"][i] for i in ids) == text, "ids decode back to the text")
        ok(meta["vocab_size"] == len(set(text)), "the vocabulary is every distinct character")
        try:
            import numpy as np
        except ImportError:
            print("  skip write: numpy is not installed here")
        else:
            out = Path(tmp) / "out"
            stats = write(corpus, out)
            train = np.fromfile(out / "train.bin", dtype=np.uint16)
            val = np.fromfile(out / "val.bin", dtype=np.uint16)
            ok(len(train) + len(val) == stats["chars"], "train and val hold every character")
            ok((out / "meta.pkl").exists(), "meta.pkl is written")
        try:
            read_corpus(Path(tmp) / "empty")
            ok(False, "an empty corpus is refused")
        except SystemExit:
            ok(True, "an empty corpus is refused")
    print("prepare_corpus self-test: " + ("ok" if not fails else f"{fails} failure(s)"))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    s = write(a.corpus, a.out)
    print(
        f"prepare_corpus: {s['chars']:,} characters, vocabulary {s['vocab']}, "
        f"train {s['train']:,}, val {s['val']:,} -> {a.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
