#!/usr/bin/env bash
# benchmark — run the pinned app image's --benchmark against the Ollama on localhost:11434, into
# data/. The app prints "(benchmark failed: …)" and still exits 0, so this fails on that line, on a
# non-zero exit, and on a run that wrote no new data/benchmark-*.md: the failure lands here, not
# in the gate after it.
#
#   scripts/benchmark.sh              # MAROLA_LOCAL_LLM_MODEL / MAROLA_LOCAL_EMBED_MODEL override the models
#   scripts/benchmark.sh --self-test
#
# The embedder is a real embedding model: Ollama starts llama-server with --embedding only for a
# GGUF that declares <arch>.pooling_type, so /api/embed on a chat model such as llama3.2 is a 501.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

newest() { find "$1" -maxdepth 1 -name 'benchmark-*.md' 2>/dev/null | LC_ALL=C sort | tail -1; }

run() (
  local image log before after
  image="${MAROLA_APP_IMAGE:-$("$root/scripts/app-image.sh")}"
  mkdir -p "$root/data"
  before="$(newest "$root/data")"
  log="$(mktemp)"
  trap 'rm -f "$log"' EXIT
  docker run --rm --network host --user "$(id -u):$(id -g)" -e HOME=/tmp \
    -e MAROLA_LOCAL_LLM_MODEL="${MAROLA_LOCAL_LLM_MODEL:-marola-llama3.2}" \
    -e MAROLA_LOCAL_EMBED_MODEL="${MAROLA_LOCAL_EMBED_MODEL:-nomic-embed-text:v1.5}" \
    -v "$root/data:/app/data" "$image" --benchmark | tee "$log"
  if grep -q '^(benchmark failed' "$log"; then echo "benchmark: the app reported a failure (above)" >&2; exit 1; fi
  after="$(newest "$root/data")"
  [ -n "$after" ] && [ "$after" != "$before" ] || { echo "benchmark: no new data/benchmark-*.md" >&2; exit 1; }
  echo "benchmark: $after" >&2
)

self_test() {
  local t f=0
  t="$(mktemp -d)"
  trap 'rm -rf "$t"' RETURN
  mkdir -p "$t/repo/scripts" "$t/bin"
  cp "${BASH_SOURCE[0]}" "$t/repo/scripts/benchmark.sh"
  # A docker that records its arguments and behaves as STUB says.
  { echo "#!$BASH"; cat <<'EOF'
printf '%s\n' "$@" >"$STUB_ARGS"
data=""; prev=""
for a in "$@"; do [ "$prev" = -v ] && data="${a%%:*}"; prev="$a"; done
case "$STUB" in
  ok) echo "Saved to ./data/benchmark-20261001-1200.md"; echo report >"$data/benchmark-20261001-1200.md" ;;
  failed) echo "(benchmark failed: Failure(HTTP 501 for http://localhost:11434/api/embed))" ;;
  silent) : ;;
  crash) exit 3 ;;
esac
EOF
  } >"$t/bin/docker"
  chmod +x "$t/bin/docker"
  b() { STUB="$1" STUB_ARGS="$t/args" MAROLA_APP_IMAGE=app:pinned PATH="$t/bin:$PATH" \
    bash "$t/repo/scripts/benchmark.sh" >/dev/null 2>&1; }

  b ok || { echo "FAIL: a run that saved a report"; f=1; }
  grep -qx 'MAROLA_LOCAL_EMBED_MODEL=nomic-embed-text:v1.5' "$t/args" || { echo "FAIL: the embedder is not an embedding model"; f=1; }
  grep -qx 'app:pinned' "$t/args" || { echo "FAIL: the pinned image was not run"; f=1; }
  for stub in failed silent crash; do
    if b "$stub"; then echo "FAIL: a '$stub' run passed"; f=1; fi
  done
  if b silent; then echo "FAIL: an old report counted as this run's"; f=1; fi
  echo "benchmark self-test:" "$([ "$f" -eq 0 ] && echo ok || echo FAILED)"
  [ "$f" -eq 0 ]
}

case "${1:-}" in
  --self-test) self_test ;;
  "") run ;;
  *) echo "usage: $0 [--self-test]" >&2; exit 2 ;;
esac
