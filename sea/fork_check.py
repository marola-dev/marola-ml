"""fork_check: every file of sea/nanogpt says where it came from, and an as-is file still is.

    python3 sea/fork_check.py
    python3 sea/fork_check.py --self-test

sea/FORK.tsv lists the files copied from karpathy/nanoGPT, each with the sha256 of the upstream
file and a state. This refuses:
  - a file under sea/nanogpt that FORK.tsv does not list (what training writes there is skipped:
    data/marola_corpus/, out-*/, __pycache__/);
  - a listed file that is missing;
  - a copied file without its provenance header (the fork date, the commit, the MIT notice), except
    LICENSE, which is kept byte for byte;
  - an `as-is` file whose body, below the header, is not the upstream file any more: when marola
    edits one, its row says `edited`.
Standard library only.
"""

import hashlib
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORK = HERE / "FORK.tsv"
VENDOR = HERE / "nanogpt"
SHA = "3adf61e154c3"
SKIP = ("data/marola_corpus/", "__pycache__/")


def rows(text: str) -> dict[str, tuple[str, str]]:
    out = {}
    for line in text.splitlines():
        if not line or line.startswith("#") or line.startswith("path\t"):
            continue
        path, sha, state = line.split("\t")
        out[path] = (sha, state)
    return out


def body(path: str, text: bytes) -> bytes | None:
    """The upstream bytes below marola's header, or None when the header is not there."""
    if path == "LICENSE":
        return text
    s = text.decode("utf-8")
    if path.endswith(".py"):
        head, _, rest = s.partition("\n\n")
        ok = (
            head.startswith("# Forked into marola-dev/marola-ml on ")
            and SHA in head
            and "MIT" in head
        )
    else:
        head, _, rest = s.partition("-->\n\n")
        ok = (
            head.startswith("<!--\nForked into marola-dev/marola-ml on ")
            and SHA in head
            and "MIT" in head
        )
    return rest.encode("utf-8") if ok else None


def check(fork: Path, vendor: Path) -> list[str]:
    listed = rows(fork.read_text(encoding="utf-8"))
    errors = []
    present = {p.relative_to(vendor).as_posix() for p in vendor.rglob("*") if p.is_file()}
    present = {
        p
        for p in present
        if not p.startswith(SKIP)
        and not p.split("/")[0].startswith("out-")
        and "/__pycache__/" not in f"/{p}"
    }
    for p in sorted(present - set(listed)):
        errors.append(f"{p}: under sea/nanogpt but not in FORK.tsv")
    for p, (sha, state) in sorted(listed.items()):
        f = vendor / p
        if not f.exists():
            errors.append(f"{p}: in FORK.tsv but missing")
            continue
        b = body(p, f.read_bytes())
        if b is None:
            errors.append(f"{p}: no provenance header (fork date, commit {SHA}, MIT)")
        elif state == "as-is" and hashlib.sha256(b).hexdigest() != sha:
            errors.append(f"{p}: changed below its header but FORK.tsv says as-is; say edited")
        elif state not in ("as-is", "edited"):
            errors.append(f"{p}: state is as-is or edited, not {state}")
    return errors


def self_test() -> int:
    fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal fails
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        fails += 0 if cond else 1

    up = b"print('hi')\n"
    head = f"# Forked into marola-dev/marola-ml on 2026-10-14 from karpathy/nanoGPT at commit {SHA},\n# url\n# MIT\n\n"
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        v = t / "nanogpt"
        (v / "data" / "marola_corpus").mkdir(parents=True)
        (v / "model.py").write_bytes(head.encode() + up)
        (v / "LICENSE").write_bytes(b"MIT License\n")
        (v / "data" / "marola_corpus" / "train.bin").write_bytes(b"\0")
        fork = t / "FORK.tsv"
        good = (
            "path\tupstream_sha256\tstate\n"
            f"model.py\t{hashlib.sha256(up).hexdigest()}\tas-is\n"
            f"LICENSE\t{hashlib.sha256(b'MIT License' + bytes([10])).hexdigest()}\tas-is\n"
        )
        fork.write_text(good, encoding="utf-8")
        ok(check(fork, v) == [], "a copy with its header, and the generated data skipped, passes")
        (v / "model.py").write_bytes(head.encode() + b"print('changed')\n")
        ok(any("say edited" in e for e in check(fork, v)), "an as-is file that changed is refused")
        fork.write_text(good.replace("as-is\n", "edited\n", 1), encoding="utf-8")
        ok(check(fork, v) == [], "the same change, marked edited, passes")
        (v / "model.py").write_bytes(up)
        ok(
            any("no provenance header" in e for e in check(fork, v)),
            "a file without its header is refused",
        )
        (v / "extra.py").write_bytes(head.encode() + up)
        ok(any("not in FORK.tsv" in e for e in check(fork, v)), "an unlisted file is refused")
    print("fork_check self-test: " + ("ok" if not fails else f"{fails} failure(s)"))
    return 1 if fails else 0


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    errors = check(FORK, VENDOR)
    for e in errors:
        print(f"fork_check: {e}", file=sys.stderr)
    if errors:
        return 1
    n = len(rows(FORK.read_text(encoding="utf-8")))
    print(f"fork_check: {n} files from karpathy/nanoGPT@{SHA}, each with its provenance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
