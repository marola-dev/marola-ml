#!/usr/bin/env python3
"""benchmark_gate — the promotion gate for the marola-local image (MIP-0008 §5.3, tasks decision 9).

    scripts/benchmark_gate.py check --new data --kept docs/benchmarks [--tolerance 0.05] \
        [--questions .tmp/resources/benchmark_questions.json]
    scripts/benchmark_gate.py --self-test

`just benchmark` writes a Markdown report whose first table is the summary — one row per arm
(`baseline`, `rag-strict`, `rag-general`) with the coverage columns; the kept runs under
docs/benchmarks/ have the same table, several per file. The gate reads one number from each:
`rag-general` coverage (all), "the result that matters" in docs/benchmarks/2026-09-05.md.
It fails when the new run's number is more than `--tolerance` below the best kept one, or
below the new run's own `baseline` — marola must still beat the plain prompt. `--new`/`--kept`
accept a file or a directory (newest file by name). `--questions` is the app's question set from the
resources tarball (MIP-0070 §5.4): the new run must have answered exactly those ids on every arm, so
an image and a resources pin that drifted apart fail here. Standard library only.
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

HEADER = re.compile(r"^\|\s*arm\s*\|\s*coverage \(in-corpus\)\s*\|")
ROW = re.compile(r"^\|\s*([a-z-]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|")
METRIC_ARM = "rag-general"
PLAIN_ARM = "baseline"
ARMS = ("baseline", "rag-strict", "rag-general")
PER_QUESTION_HEADER = re.compile(r"^\|\s*id\s*\|\s*topic\s*\|")


def parse_tables(markdown: str) -> list[dict[str, dict[str, float]]]:
    """Every summary table in the text: arm -> {in_corpus, general, all}."""
    tables: list[dict[str, dict[str, float]]] = []
    current: dict[str, dict[str, float]] | None = None
    for line in markdown.splitlines():
        if HEADER.match(line):
            current = {}
            tables.append(current)
        elif current is not None and (m := ROW.match(line)):
            current[m.group(1)] = {
                "in_corpus": float(m.group(2)),
                "general": float(m.group(3)),
                "all": float(m.group(4)),
            }
        elif current is not None and not line.startswith("|"):
            current = None
    return [t for t in tables if t]


def newest(path: Path) -> Path:
    if path.is_dir():
        files = sorted(p for p in path.glob("*.md") if p.is_file())
        if not files:
            raise SystemExit(f"benchmark_gate: no *.md under {path}")
        return files[-1]
    return path


def metric(table: dict[str, dict[str, float]], arm: str) -> float | None:
    row = table.get(arm)
    return None if row is None else row["all"]


def check(new_md: str, kept_md: str, tolerance: float) -> tuple[bool, list[str]]:
    new_tables = parse_tables(new_md)
    kept_tables = parse_tables(kept_md)
    lines: list[str] = []
    if not new_tables:
        return False, ["no summary table in the new benchmark"]
    if not kept_tables:
        return False, ["no summary table in the kept benchmark"]
    new = new_tables[0]
    got = metric(new, METRIC_ARM)
    plain = metric(new, PLAIN_ARM)
    kept_best = max((metric(t, METRIC_ARM) or 0.0) for t in kept_tables)
    if got is None or plain is None:
        return False, [f"the new benchmark lacks a {METRIC_ARM} or {PLAIN_ARM} row"]
    ok = True
    lines.append(
        f"{METRIC_ARM} coverage (all): new {got:.2f}, best kept {kept_best:.2f}, tolerance {tolerance:.2f}"
    )
    if got < kept_best - tolerance:
        ok = False
        lines.append(f"FAIL: {got:.2f} is more than {tolerance:.2f} below the kept {kept_best:.2f}")
        lines.append(
            "  after a deliberate model or embedder change: commit this run's report as "
            "docs/benchmarks/<date>.md (it becomes the newest kept run), see docs/index.md"
        )
    lines.append(f"{PLAIN_ARM} coverage (all) in the new run: {plain:.2f}")
    if got < plain:
        ok = False
        lines.append(
            f"FAIL: {METRIC_ARM} {got:.2f} is below the plain prompt {plain:.2f} — marola no longer beats it"
        )
    lines.append("PASS" if ok else "the model is not promoted")
    return ok, lines


def question_problems(new_md: str, questions: list[dict]) -> list[str]:
    """What the new run's per-question table lacks, or has extra, against the question set."""
    if not questions:
        return ["the question set is empty"]
    seen: set[tuple[str, str]] = set()
    in_table = False
    for line in new_md.splitlines():
        if PER_QUESTION_HEADER.match(line):
            in_table = True
        elif in_table and line.startswith("|") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4:
                seen.add((cells[0], cells[3]))
        elif in_table and not line.startswith("|"):
            in_table = False
    if not seen:
        return ["no per-question table in the new benchmark"]
    want = {(q["id"], arm) for q in questions for arm in ARMS}
    problems = [f"missing: {qid} on {arm}" for qid, arm in sorted(want - seen)]
    problems += [f"not in the question set: {qid} on {arm}" for qid, arm in sorted(seen - want)]
    return problems


def self_test() -> int:
    kept_dir = Path(__file__).resolve().parent.parent / "docs" / "benchmarks"
    kept = newest(kept_dir).read_text()
    tables = parse_tables(kept)
    assert len(tables) >= 2, f"expected several runs in {kept_dir}, parsed {len(tables)}"
    best = max(metric(t, METRIC_ARM) for t in tables)
    assert abs(best - 0.84) < 1e-9, best  # run 2 of docs/benchmarks/2026-09-05.md

    good = "| arm | coverage (in-corpus) | coverage (general) | coverage (all) | cited | abstained | mean ms |\n|---|---|---|---|---|---|---|\n"
    good += "| baseline | 0.52 | 0.92 | 0.73 | 0% | 0% | 479 |\n| rag-strict | 0.67 | 0.03 | 0.32 | 41% | 55% | 322 |\n| rag-general | 0.88 | 0.79 | 0.83 | 36% | 0% | 545 |\n"
    ok, out = check(good, kept, 0.05)
    assert ok, out
    ok, out = check(good.replace("| 0.83 |", "| 0.70 |"), kept, 0.05)
    assert not ok and any("below the kept" in line for line in out), out
    assert any("docs/benchmarks/" in line for line in out), "the failure names no way forward"
    ok, out = check(
        good.replace("| 0.73 |", "| 0.90 |").replace("| 0.83 |", "| 0.80 |"), kept, 0.05
    )
    assert not ok and any("plain prompt" in line for line in out), out
    ok, out = check("# nothing here\n", kept, 0.05)
    assert not ok and "no summary table" in out[0]
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "benchmark-20260901-0000.md").write_text(good.replace("| 0.83 |", "| 0.10 |"))
        (d / "benchmark-20260905-0950.md").write_text(good)
        assert newest(d).name == "benchmark-20260905-0950.md"

    questions = [{"id": "q01"}, {"id": "q02"}]
    per_q = "\n## Per question\n\n| id | topic | in corpus | arm | coverage | cited | abstained | ms | answer (first 140 chars) |\n|---|---|---|---|---|---|---|---|---|\n"
    full = (
        good
        + per_q
        + "".join(
            f"| {q['id']} | safety | yes | {arm} | 1.00 | | | 1 | a |\n"
            for q in questions
            for arm in ARMS
        )
    )
    assert question_problems(full, questions) == [], question_problems(full, questions)
    partial = full.replace(
        "| q02 | safety | yes | rag-general |", "| q03 | safety | yes | rag-general |"
    )
    probs = question_problems(partial, questions)
    assert any("q02" in p for p in probs) and any("q03" in p for p in probs), probs
    assert question_problems(good, questions), "a report with no per-question table passed"
    assert question_problems(full, []), "an empty question set passed"
    print(f"benchmark_gate self-test: ok (kept best {METRIC_ARM} = {best:.2f})")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    chk = sub.add_parser("check")
    chk.add_argument(
        "--new", required=True, type=Path, help="a benchmark report, or the directory data/"
    )
    chk.add_argument("--kept", default=Path("docs/benchmarks"), type=Path)
    chk.add_argument("--tolerance", default=0.05, type=float)
    chk.add_argument("--questions", type=Path, help="benchmark_questions.json (resources tarball)")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.cmd != "check":
        ap.print_help()
        return 2
    new_path, kept_path = newest(args.new), newest(args.kept)
    print(f"new: {new_path}\nkept: {kept_path}")
    ok, lines = check(new_path.read_text(), kept_path.read_text(), args.tolerance)
    if args.questions is not None:
        problems = question_problems(new_path.read_text(), json.loads(args.questions.read_text()))
        if problems:
            ok = False
            lines = lines[:-1] + [f"FAIL: {p} ({args.questions})" for p in problems]
            lines.append("the model is not promoted")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
