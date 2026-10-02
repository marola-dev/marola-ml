#!/usr/bin/env bash
# resources-fetch — unpack the app's resources tarball pinned in resources.version into
# .tmp/resources (MIP-0070 §5.4): the compiled prompts and sea lore finetune/ reads, and the
# benchmark question set the gate checks a run against. A release asset, not a CI artifact: it
# needs no token and does not expire. A pin already fetched is not downloaded again
# (.tmp/resources.version).
#
#   scripts/resources-fetch.sh              # resolve the pin in the repo root's resources.version
#   scripts/resources-fetch.sh --self-test
#
# MAROLA_RESOURCES_URL overrides the release base (the self-test serves file:// fixtures). The
# default is marola-app's releases, whose release.yml attaches the tarball to each v* tag.
set -euo pipefail

FILES=(recommendation_prompt.json review_prompt.json sea_lore.json benchmark_questions.json)

fetch() {
  local root="$1" pin base
  pin="$(<"$root/resources.version")"
  [[ "$pin" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "resources-fetch: resources.version must be an app release tag (vX.Y.Z), got '$pin'" >&2; return 1; }
  if [ -d "$root/.tmp/resources" ] && [ "$(cat "$root/.tmp/resources.version" 2>/dev/null)" = "$pin" ]; then
    return 0
  fi
  base="${MAROLA_RESOURCES_URL:-https://github.com/marola-dev/marola-app/releases/download}"
  mkdir -p "$root/.tmp"
  (
    tmp="$(mktemp -d "$root/.tmp/resources-fetch.XXXXXX")"
    trap 'rm -rf "$tmp"' EXIT
    curl -fsSL --retry 3 -o "$tmp/resources.tar.gz" "$base/$pin/ml-resources-$pin.tar.gz" ||
      { echo "resources-fetch: could not download ml-resources $pin from $base" >&2; exit 1; }
    mkdir "$tmp/resources"
    tar -xzf "$tmp/resources.tar.gz" -C "$tmp/resources"
    for f in "${FILES[@]}"; do
      [ -s "$tmp/resources/$f" ] || { echo "resources-fetch: ml-resources $pin has no $f" >&2; exit 1; }
    done
    rm -rf "$root/.tmp/resources"
    mv "$tmp/resources" "$root/.tmp/resources"
    echo "$pin" >"$root/.tmp/resources.version"
    echo "resources-fetch: ml-resources $pin -> .tmp/resources" >&2
  )
}

self_test() {
  local t f=0 out
  t="$(mktemp -d)"
  trap 'rm -rf "$t"' RETURN
  # Fake releases, laid out as GitHub serves them: <base>/<tag>/ml-resources-<tag>.tar.gz, flat.
  release() {
    local tag=$1 src="$t/src-$1"
    shift
    mkdir -p "$src" "$t/releases/$tag"
    for file in "$@"; do echo "{\"tag\": \"$tag\"}" >"$src/$file"; done
    tar -czf "$t/releases/$tag/ml-resources-$tag.tar.gz" -C "$src" "$@"
  }
  release v0.1.0 "${FILES[@]}" board.json
  release v0.2.0 "${FILES[@]}"
  release v0.3.0 recommendation_prompt.json review_prompt.json sea_lore.json
  mkdir -p "$t/releases/v0.4.0"
  head -c 40 "$t/releases/v0.1.0/ml-resources-v0.1.0.tar.gz" >"$t/releases/v0.4.0/ml-resources-v0.4.0.tar.gz"
  mkdir -p "$t/repo"
  export MAROLA_RESOURCES_URL="file://$t/releases"
  run_fetch() { bash -euo pipefail -c "FILES=(${FILES[*]}); $(declare -f fetch); fetch \"\$1\"" _ "$t/repo" 2>/dev/null; }

  echo v0.1.0 >"$t/repo/resources.version"
  out="$(run_fetch)" || { echo "FAIL: fetch v0.1.0"; f=1; }
  [ -z "$out" ] || { echo "FAIL: fetch wrote to stdout: $out"; f=1; }
  for file in "${FILES[@]}"; do
    [ -f "$t/repo/.tmp/resources/$file" ] || { echo "FAIL: $file missing after fetch"; f=1; }
  done

  MAROLA_RESOURCES_URL="file://$t/nowhere" run_fetch || { echo "FAIL: a re-run of the same pin downloaded again"; f=1; }

  echo v0.2.0 >"$t/repo/resources.version"
  run_fetch || { echo "FAIL: fetch v0.2.0"; f=1; }
  grep -q v0.2.0 "$t/repo/.tmp/resources/sea_lore.json" || { echo "FAIL: the bump did not replace sea_lore.json"; f=1; }
  [ -f "$t/repo/.tmp/resources/board.json" ] && { echo "FAIL: a file v0.2.0 dropped survived the bump"; f=1; }

  # No release, a tarball missing a file the readers need, a truncated one, a bad pin: the last
  # good tree and its recorded version stay.
  for pin in v9.9.9 v0.3.0 v0.4.0 latest; do
    echo "$pin" >"$t/repo/resources.version"
    if run_fetch; then echo "FAIL: pin $pin should exit non-zero"; f=1; fi
    grep -q v0.2.0 "$t/repo/.tmp/resources/sea_lore.json" || { echo "FAIL: pin $pin removed the last good tree"; f=1; }
    [ "$(cat "$t/repo/.tmp/resources.version")" = v0.2.0 ] || { echo "FAIL: pin $pin moved the recorded version"; f=1; }
  done

  echo "resources-fetch self-test:" "$([ "$f" -eq 0 ] && echo ok || echo FAILED)"
  [ "$f" -eq 0 ]
}

case "${1:-}" in
  --self-test) self_test ;;
  "") fetch "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" ;;
  *) echo "usage: $0 [--self-test]" >&2; exit 2 ;;
esac
