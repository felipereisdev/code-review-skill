#!/usr/bin/env bash
# Negative tests for scripts/check-docs.sh: each broken copy of the repo must FAIL with a specific message.
# Usage: bash scripts/test-check-docs.sh   (exits 1 if any test fails)
set -u
cd "$(dirname "$0")/.." || exit 1

failures=0
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Copies tracked and untracked-but-not-ignored files (working-tree content) into a new git repo at $1.
make_copy() {
  mkdir -p "$1"
  git ls-files -z --cached --others --exclude-standard | tar -cf - --null -T - | tar -xf - -C "$1"
  git -C "$1" init -q
  git -C "$1" add -A
}

# expect_fail <test name> <copy dir> <text that must appear in the check-docs output>
expect_fail() {
  local out rc
  out=$(bash "$2/scripts/check-docs.sh" 2>&1)
  rc=$?
  if [ "$rc" -ne 0 ] && printf '%s\n' "$out" | grep -qF -- "$3"; then
    printf 'PASS %s\n' "$1"
  else
    printf 'FAIL %s (exit %s; output must contain: %s)\n' "$1" "$rc" "$3"
    failures=$((failures + 1))
  fi
}

make_copy "$work/unmodified"
if bash "$work/unmodified/scripts/check-docs.sh" > /dev/null 2>&1; then
  printf 'PASS unmodified copy passes check-docs\n'
else
  printf 'FAIL unmodified copy should pass check-docs\n'
  failures=$((failures + 1))
fi

make_copy "$work/missing"
printf -- '- `./stacks/does-not-exist.md`\n' >> "$work/missing/SKILL.md"
expect_fail "citing a missing file fails" "$work/missing" "SKILL.md cites missing file: stacks/does-not-exist.md"

make_copy "$work/deleted"
rm "$work/deleted/stacks/kafka.md"
expect_fail "deleting a cited stack file fails" "$work/deleted" "SKILL.md cites missing file: stacks/kafka.md"

make_copy "$work/orphan"
printf '# Elixir\n' > "$work/orphan/stacks/elixir.md"
expect_fail "an uncited stack file fails" "$work/orphan" "stacks/elixir.md is not cited in SKILL.md"

# drop_lines <file> <fixed text>: removes every line of <file> that contains <fixed text>.
drop_lines() {
  grep -vF -- "$2" "$1" > "$1.tmp"
  mv "$1.tmp" "$1"
}

make_copy "$work/nocap"
drop_lines "$work/nocap/SKILL.md" 'is never above **Warning**'
expect_fail "removing the verify/ensure severity cap fails" "$work/nocap" "SKILL.md is missing: is never above **Warning**"

make_copy "$work/oldformat"
drop_lines "$work/oldformat/SKILL.md" '**Location:** `path/to/file.ext:start-end`'
expect_fail "removing the Location field fails" "$work/oldformat" "SKILL.md is missing: **Location:** \`path/to/file.ext:start-end\`"
make_copy "$work/nodeletionrule"
drop_lines "$work/nodeletionrule/SKILL.md" '**Deletion-only exception:**'
expect_fail "removing the deletion-only Location exception fails" "$work/nodeletionrule" "SKILL.md is missing: **Deletion-only exception:**"
make_copy "$work/nocompactdeletion"
drop_lines "$work/nocompactdeletion/SKILL.md" 'same deletion-only exception'
expect_fail "compact mode must inherit the deletion-only exception" "$work/nocompactdeletion" "SKILL.md is missing: same deletion-only exception"

# replace_first <file> <old> <new>: replaces the first occurrence of <old> in <file>.
replace_first() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
path, old, new = sys.argv[1:]
text = open(path, encoding="utf-8").read()
open(path, "w", encoding="utf-8").write(text.replace(old, new, 1))
PY
}

make_copy "$work/noevidence"
drop_lines "$work/noevidence/example-output.md" '**Evidence:**'
expect_fail "an example finding without Evidence fails" "$work/noevidence" "has no **Evidence:** line"

make_copy "$work/lowconf"
replace_first "$work/lowconf/example-output.md" '**Confidence:** High' '**Confidence:** Low'
expect_fail "a Low-confidence example finding fails" "$work/lowconf" "example-output.md reports a Low-confidence finding"

make_copy "$work/badtotal"
replace_first "$work/badtotal/example-output.md" '| **Total** | **2** |' '| **Total** | **3** |'
expect_fail "a Summary total that does not match the findings fails" "$work/badtotal" "Summary Total row is [3, 1, 5]"

make_copy "$work/slowpath"
drop_lines "$work/slowpath/SKILL.md" 'do work or queries that grow with data size'
expect_fail "removing the hot-path performance severity rule fails" "$work/slowpath" "SKILL.md is missing: do work or queries that grow with data size"

if [ "$failures" -gt 0 ]; then
  printf '%d test(s) failed\n' "$failures"
  exit 1
fi
printf 'All negative tests passed\n'
