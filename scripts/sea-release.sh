#!/usr/bin/env bash
# sea-release — release marolaGPT: tag main as marolagpt-vX.Y.Z and push the tag. The tag is the
# pattern that publishes: marola-gpt-publish.yml runs on a pushed `marolagpt-v*` tag (and by hand),
# never on a merge, so main can move for weeks without touching Hugging Face. The workflow then
# trains marolaGPT from the pinned corpus, packages it and uploads it to h0ffmann/marolaGPT, tagged
# v<X.Y.Z> there. An upload cannot be taken back, so this refuses anything but a clean main, level
# with origin, whose CI passed, and a version that goes up.
#
#   just sea-release                       # the next patch: marolagpt-v0.1.0 first, then 0.1.1, ...
#   just sea-release minor|major|X.Y.Z     # another bump, or an exact version
#   just sea-release patch --dry-run       # every check, and the tag it would push; pushes nothing
#   scripts/sea-release.sh --self-test
#
# The owner's to run: marola-ml's AGENTS.md has agents create no tag (`.claude/settings.json` denies
# `git tag`). The shape is closed-source's and marola's scripts/release.sh.
set -euo pipefail

PREFIX=marolagpt-v

valid() { [[ "$1" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; }

# bump <X.Y.Z or empty> <major|minor|patch>: the next version; the first release is 0.1.0
bump() {
  local major minor patch
  [ -n "$1" ] || { echo "0.1.0"; return; }
  IFS=. read -r major minor patch <<<"$1"
  case "$2" in
    major) echo "$((major + 1)).0.0" ;;
    minor) echo "$major.$((minor + 1)).0" ;;
    patch) echo "$major.$minor.$((patch + 1))" ;;
  esac
}

# newer <a> <b>: a sorts strictly after b (b may be empty)
newer() { [ -z "$2" ] || { [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -1)" = "$1" ]; }; }

# latest: the highest marolagpt-v* tag's version, or nothing
latest() { git tag -l "${PREFIX}*" | sed "s/^${PREFIX}//" | while read -r v; do valid "$v" && echo "$v"; done | sort -V | tail -1; }

if [ "${1:-}" = --self-test ]; then
  fail() { echo "sea-release: self-test: $*" >&2; exit 1; }
  for v in 0.1.0 1.0.0 10.20.30; do valid "$v" || fail "rejected $v"; done
  for v in v0.1.0 0.1 0.1.0-rc1 01.2.3 1.2.3.4; do ! valid "$v" || fail "accepted $v"; done
  [ "$(bump "" patch)" = 0.1.0 ] || fail "the first release is not 0.1.0"
  [ "$(bump 0.1.9 patch)" = 0.1.10 ] || fail "0.1.9 + patch"
  [ "$(bump 0.1.9 minor)" = 0.2.0 ] || fail "0.1.9 + minor"
  [ "$(bump 1.4.2 major)" = 2.0.0 ] || fail "1.4.2 + major"
  newer 0.10.0 0.9.0 || fail "0.10.0 not newer than 0.9.0"
  newer 0.1.0 "" || fail "a first version is not newer than nothing"
  ! newer 0.1.0 0.1.0 || fail "a version is newer than itself"
  echo "sea-release: self-test ok" >&2
  exit 0
fi

dry_run=0 want=patch
for a in "$@"; do
  case "$a" in
    --dry-run) dry_run=1 ;;
    *) want="$a" ;;
  esac
done

cd "$(git rev-parse --show-toplevel)"
git fetch -q --tags origin main
prev="$(latest)"
case "$want" in
  major | minor | patch) next="$(bump "$prev" "$want")" ;;
  *) next="${want#"$PREFIX"}" ;;
esac
valid "$next" || { echo "sea-release: '$want' is not major, minor, patch or X.Y.Z" >&2; exit 1; }
newer "$next" "$prev" || { echo "sea-release: $next does not come after ${prev:-nothing}" >&2; exit 1; }
tag="$PREFIX$next"
git rev-parse -q --verify "refs/tags/$tag" >/dev/null && { echo "sea-release: $tag already exists" >&2; exit 1; }
[ "$(git branch --show-current)" = main ] || { echo "sea-release: check out main first" >&2; exit 1; }
# " A" is intent-to-add, which stages no content: `nix develop` marks an untracked flake.lock so.
[ -z "$(git status --porcelain --untracked-files=no | grep -v '^ A ' || true)" ] \
  || { echo "sea-release: the working tree is dirty; commit or stash first" >&2; exit 1; }
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] \
  || { echo "sea-release: main is not level with origin/main; pull first" >&2; exit 1; }
head="$(git rev-parse HEAD)"
ci="$(gh run list --workflow ci.yml --commit "$head" --limit 1 --json conclusion --jq '.[0].conclusion // ""' 2>/dev/null || true)"
[ "$ci" = success ] || { echo "sea-release: CI on main at ${head:0:7} is '${ci:-not found}', not success" >&2; exit 1; }

since="${prev:+$PREFIX$prev..}HEAD"
echo "sea-release: $tag at $(git log -1 --format='%h %s') (previous: ${prev:+$PREFIX$prev}${prev:-none})" >&2
echo "sea-release: $(git rev-list --count "$since") commits since; marola-gpt-publish.yml will train, package and upload marolaGPT $next to h0ffmann/marolaGPT" >&2
if [ "$dry_run" -eq 1 ]; then
  echo "+ git tag -a $tag -m 'marolaGPT $next'" >&2
  echo "+ git push origin $tag" >&2
  exit 0
fi
git tag -a "$tag" -m "marolaGPT $next"
git push origin "$tag"
echo "sea-release: pushed $tag; follow it with: gh run list --workflow marola-gpt-publish.yml --limit 1" >&2
