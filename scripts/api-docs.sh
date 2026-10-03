#!/usr/bin/env bash
# api-docs — pdoc over finetune/ and scripts/. The name and layout of the default [out-dir] mode is
# the umbrella's old contract (its scripts/fetch-api-docs.sh unpacks the latest release's
# api-docs.tar.gz under repos/marola-ml/api/, MIP-0070 §5.5); --dir is MIP-0074 §5.2's: the devkit's
# api-docs.yml runs `just api-docs <out>` as a PR check and, on a push, publishes it to the
# `api-docs` branch. Either way the umbrella's docs build fails on a third-party <script src>, so
# this fails it first.
#
#   scripts/api-docs.sh [out-dir]   # default .tmp: <out-dir>/api-docs.tar.gz (release.yml's asset)
#   scripts/api-docs.sh --dir <out> # <out>/python/, raw pages (the devkit api-docs.yml caller)
#   scripts/api-docs.sh --self-test
#
# PDOC overrides the pdoc command (default `python3 -m pdoc`; the self-test stubs it).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# pdoc's html at $1 (created if missing); fails on no output or a third-party <script src>.
generate() {
  local dest="$1" pdoc
  read -ra pdoc <<<"${PDOC:-python3 -m pdoc}"
  mkdir -p "$dest"
  # finetune/ keeps torch/peft/trl behind lazy imports, so pdoc imports it without the ML stack.
  (cd "$root" && "${pdoc[@]}" -o "$dest" finetune/*.py scripts/*.py) >&2
  [ -f "$dest/index.html" ] || { echo "api-docs: pdoc wrote no index.html" >&2; exit 1; }
  if grep -rlE "<script[^>]*src=[\"']https?://" "$dest" >&2; then
    echo "api-docs: third-party <script src> in the pages above" >&2
    exit 1
  fi
}

# A subshell, so the EXIT trap cleans up without touching the caller's traps.
build() (
  local out="$1" work
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT
  generate "$work/api"
  mkdir -p "$out"
  tar -czf "$out/api-docs.tar.gz" -C "$work/api" .
  echo "api-docs: $out/api-docs.tar.gz" >&2
)

# <out>/python/, the raw layout the umbrella's api-docs branches expect (MIP-0074 §5.2).
build_dir() (
  local out="$1"
  generate "$out/python"
  echo "api-docs: $out/python" >&2
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
  STUB=clean build_dir "$t/dirok" 2>/dev/null || { echo "FAIL: --dir with a clean pdoc run"; f=1; }
  [ -f "$t/dirok/python/index.html" ] && [ -f "$t/dirok/python/build_dataset.html" ] \
    || { echo "FAIL: --dir did not write the pages under python/"; f=1; }
  [ ! -e "$t/dirok/python/api-docs.tar.gz" ] || { echo "FAIL: --dir produced a tarball"; f=1; }
  if STUB=external build_dir "$t/dirext" 2>/dev/null; then echo "FAIL: --dir allowed a third-party script"; f=1; fi
  echo "api-docs self-test:" "$([ "$f" -eq 0 ] && echo ok || echo FAILED)"
  [ "$f" -eq 0 ]
}

case "${1:-}" in
  --self-test) self_test ;;
  --dir) [ -n "${2:-}" ] || { echo "usage: $0 --dir <out-dir>" >&2; exit 2; }; build_dir "$2" ;;
  -*) echo "usage: $0 [out-dir] | --dir <out-dir> | --self-test" >&2; exit 2 ;;
  *) build "${1:-.tmp}" ;;
esac
