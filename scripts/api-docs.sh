#!/usr/bin/env bash
# api-docs — pdoc over finetune/ and scripts/ as api-docs.tar.gz, the asset release.yml attaches to
# each v* release. The name and layout are the umbrella's contract (its scripts/fetch-api-docs.sh
# unpacks the latest release's api-docs.tar.gz under repos/marola-ml/api/, MIP-0070 §5.5), and its
# docs build fails on a third-party <script src>, so one here fails this first.
#
#   scripts/api-docs.sh [out-dir]   # default .tmp: <out-dir>/api-docs.tar.gz
#   scripts/api-docs.sh --self-test
#
# PDOC overrides the pdoc command (default `python3 -m pdoc`; the self-test stubs it).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# A subshell, so the EXIT trap cleans up without touching the caller's traps.
build() (
  local out="$1" work pdoc
  read -ra pdoc <<<"${PDOC:-python3 -m pdoc}"
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT
  # finetune/ keeps torch/peft/trl behind lazy imports, so pdoc imports it without the ML stack.
  (cd "$root" && "${pdoc[@]}" -o "$work/api" finetune/*.py scripts/*.py) >&2
  [ -f "$work/api/index.html" ] || { echo "api-docs: pdoc wrote no index.html" >&2; exit 1; }
  if grep -rlE "<script[^>]*src=[\"']https?://" "$work/api" >&2; then
    echo "api-docs: third-party <script src> in the pages above" >&2
    exit 1
  fi
  mkdir -p "$out"
  tar -czf "$out/api-docs.tar.gz" -C "$work/api" .
  echo "api-docs: $out/api-docs.tar.gz" >&2
)

self_test() {
  local t f=0
  t="$(mktemp -d)"
  trap 'rm -rf "$t"' RETURN
  # A pdoc that writes what STUB says: a clean page, one loading a CDN script, or nothing.
  { echo "#!$BASH"; cat <<'EOF'
dir="$2"; mkdir -p "$dir"
case "$STUB" in
  clean) echo '<html><script>local()</script></html>' >"$dir/index.html"; echo m >"$dir/build_dataset.html" ;;
  external) echo '<html><script src="https://cdn.example/x.js"></script></html>' >"$dir/index.html" ;;
  empty) : ;;
esac
EOF
  } >"$t/pdoc"
  chmod +x "$t/pdoc"
  export PDOC="$t/pdoc"
  STUB=clean build "$t/ok" 2>/dev/null || { echo "FAIL: a clean pdoc run"; f=1; }
  [ "$(tar -tzf "$t/ok/api-docs.tar.gz" | sort | tr '\n' ' ')" = "./ ./build_dataset.html ./index.html " ] \
    || { echo "FAIL: the pages are not at the tarball root"; f=1; }
  if STUB=external build "$t/ext" 2>/dev/null; then echo "FAIL: a third-party script passed"; f=1; fi
  if STUB=empty build "$t/empty" 2>/dev/null; then echo "FAIL: an empty pdoc run passed"; f=1; fi
  [ ! -e "$t/ext/api-docs.tar.gz" ] && [ ! -e "$t/empty/api-docs.tar.gz" ] || { echo "FAIL: a failed run left a tarball"; f=1; }
  echo "api-docs self-test:" "$([ "$f" -eq 0 ] && echo ok || echo FAILED)"
  [ "$f" -eq 0 ]
}

case "${1:-}" in
  --self-test) self_test ;;
  -*) echo "usage: $0 [out-dir] | --self-test" >&2; exit 2 ;;
  *) build "${1:-.tmp}" ;;
esac
