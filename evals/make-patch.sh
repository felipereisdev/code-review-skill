#!/usr/bin/env bash
# Builds a case patch: the pair's base/ tree overlaid with the files in <after-dir>, as a staged git diff.
# Usage: bash evals/make-patch.sh <pair-dir> <after-dir> <out.patch>
# <after-dir> holds only the files that change, at their paths relative to base/. Deletions are not supported.
set -eu
if [ "$#" -ne 3 ]; then
  echo "usage: bash evals/make-patch.sh <pair-dir> <after-dir> <out.patch>" >&2
  exit 2
fi
pair_dir=$1
after_dir=$2
out=$3
[ -d "$pair_dir/base" ] || { echo "missing $pair_dir/base" >&2; exit 1; }
[ -d "$after_dir" ] || { echo "missing $after_dir" >&2; exit 1; }

repo=$(mktemp -d)
trap 'rm -rf "$repo"' EXIT
cp -R "$pair_dir/base/." "$repo/"
git -C "$repo" init -q
git -C "$repo" add -A
git -C "$repo" -c user.name=code-review-eval -c user.email=eval@example.invalid commit -q -m base
cp -R "$after_dir/." "$repo/"
git -C "$repo" add -A
git -C "$repo" -c core.quotepath=false diff --cached --no-color --no-ext-diff \
  --src-prefix=a/ --dst-prefix=b/ > "$out.tmp"
if [ ! -s "$out.tmp" ]; then
  rm -f "$out.tmp"
  echo "no changes between $pair_dir/base and $after_dir" >&2
  exit 1
fi
mv "$out.tmp" "$out"
