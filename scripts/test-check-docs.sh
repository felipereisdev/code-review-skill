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

# move_section_to_end <file> <heading>: moves the section that starts at the line <heading> to the end of <file>.
move_section_to_end() {
  python3 - "$1" "$2" <<'PY'
import sys
path, heading = sys.argv[1:]
lines = open(path, encoding="utf-8").read().splitlines()
start = lines.index(heading)
end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
open(path, "w", encoding="utf-8").write("\n".join(lines[:start] + lines[end:] + [""] + lines[start:end]) + "\n")
PY
}

make_copy "$work/noverify"
drop_lines "$work/noverify/SKILL.md" '## Step 2 — Verify Findings'
expect_fail "removing the verification step fails" "$work/noverify" "SKILL.md has no '## Step 2 — Verify Findings' section"

make_copy "$work/lateverify"
move_section_to_end "$work/lateverify/SKILL.md" '## Step 2 — Verify Findings'
expect_fail "verifying after the report sections fails" "$work/lateverify" "'## Step 2 — Verify Findings' must come after '## 13.' and before '## 14. What Was Done Well'"

make_copy "$work/norefuted"
drop_lines "$work/norefuted/SKILL.md" '**REFUTED**'
expect_fail "removing the REFUTED result fails" "$work/norefuted" "Step 2 — Verify Findings is missing: **REFUTED**"

make_copy "$work/verifysuggestions"
drop_lines "$work/verifysuggestions/SKILL.md" 'Suggestions skip this step'
expect_fail "dropping the Suggestion exemption fails" "$work/verifysuggestions" "Step 2 — Verify Findings is missing: Suggestions skip this step"

make_copy "$work/toolname"
replace_first "$work/toolname/SKILL.md" '**With subagents** (' '**With subagents** (use the Task tool; '
expect_fail "naming an agent-specific tool in the verification step fails" "$work/toolname" "Step 2 — Verify Findings names an agent-specific tool: Task tool"

make_copy "$work/nocount"
drop_lines "$work/nocount/SKILL.md" '**Verification:** <checked>'
expect_fail "removing the refuted-count line from Output Format fails" "$work/nocount" "Output Format is missing: **Verification:** <checked> Critical/Warning candidates checked, <refuted> refuted."

make_copy "$work/noverifyline"
drop_lines "$work/noverifyline/example-output.md" '**Verification:**'
expect_fail "an example without the verification line fails" "$work/noverifyline" "must have 2 **Verification:** lines (full report and compact mode), found 0"

make_copy "$work/verifymismatch"
replace_first "$work/verifymismatch/example-output.md" '5 Critical/Warning candidates checked, 1 refuted.' '6 Critical/Warning candidates checked, 1 refuted.'
expect_fail "full and compact verification lines that disagree fail" "$work/verifymismatch" "the full-report and compact-mode **Verification:** lines must match"

make_copy "$work/verifybeforetotal"
python3 - "$work/verifybeforetotal/example-output.md" <<'PY'
import sys

path = sys.argv[1]
lines = open(path, encoding="utf-8").read().splitlines()
line = "**Verification:** 5 Critical/Warning candidates checked, 1 refuted."
lines.pop(lines.index(line))
lines.insert(next(i for i, text in enumerate(lines) if text.startswith("| **Total**")), line)
open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
expect_fail "a verification line before the Summary table fails" "$work/verifybeforetotal" "the full-report **Verification:** line must come after the Summary table"

make_copy "$work/fewsurvivors"
replace_first "$work/fewsurvivors/example-output.md" '5 Critical/Warning candidates checked, 1 refuted.' '4 Critical/Warning candidates checked, 1 refuted.'
replace_first "$work/fewsurvivors/example-output.md" '5 Critical/Warning candidates checked, 1 refuted.' '4 Critical/Warning candidates checked, 1 refuted.'
expect_fail "fewer unrefuted candidates than reported findings fails" "$work/fewsurvivors" "leaves 3 unrefuted candidates but the full report has 4 Critical/Warning findings"

make_copy "$work/norefutedexample"
replace_first "$work/norefutedexample/example-output.md" '5 Critical/Warning candidates checked, 1 refuted.' '4 Critical/Warning candidates checked, 0 refuted.'
replace_first "$work/norefutedexample/example-output.md" '5 Critical/Warning candidates checked, 1 refuted.' '4 Critical/Warning candidates checked, 0 refuted.'
expect_fail "an example with no refuted candidate fails" "$work/norefutedexample" "must show at least 1 refuted candidate"

make_copy "$work/noverifyevidence"
replace_first "$work/noverifyevidence/example-output.md" 'Verification checked' 'It checked'
replace_first "$work/noverifyevidence/example-output.md" 'Verification checked' 'It checked'
expect_fail "an example whose Evidence never cites verification fails" "$work/noverifyevidence" "no example finding's Evidence names what verification checked"

make_copy "$work/nodonotreport"
drop_lines "$work/nodonotreport/SKILL.md" '## Do Not Report'
expect_fail "removing the Do Not Report section fails" "$work/nodonotreport" "SKILL.md has no '## Do Not Report' section"

make_copy "$work/latedonotreport"
move_section_to_end "$work/latedonotreport/SKILL.md" '## Do Not Report'
expect_fail "a Do Not Report section after the checklist fails" "$work/latedonotreport" "'## Do Not Report' must come after '## Evidence and Confidence' and before '## Step 1 — Codebase Investigation'"

make_copy "$work/nosilenced"
drop_lines "$work/nosilenced/SKILL.md" '**Silenced rules**'
expect_fail "removing a Do Not Report item fails" "$work/nosilenced" "Do Not Report is missing: **Silenced rules**"

make_copy "$work/nowhy"
replace_first "$work/nowhy/SKILL.md" ' Why: ' ' Because: '
expect_fail "a Do Not Report item without Why fails" "$work/nowhy" "Do Not Report item has no 'Why:': Pre-existing problems"

make_copy "$work/nocarveout"
drop_lines "$work/nocarveout/SKILL.md" 'When a changed line triggers a problem in old code, report it'
expect_fail "dropping the changed-line carve-out fails" "$work/nocarveout" "Do Not Report is missing: When a changed line triggers a problem in old code, report it"

make_copy "$work/nocountrule"
drop_lines "$work/nocountrule/SKILL.md" 'counts as refuted on the verification line'
expect_fail "dropping the refuted-count rule fails" "$work/nocountrule" "Do Not Report is missing: counts as refuted on the verification line"

make_copy "$work/parked"
drop_lines "$work/parked/SKILL.md" 'Do not move a matching finding to'
expect_fail "allowing matches in Needs human verification fails" "$work/parked" "Do Not Report is missing: Do not move a matching finding to \`## Needs human verification\`"

make_copy "$work/noprecedentload"
drop_lines "$work/noprecedentload/SKILL.md" "unless that precedent's **Exception:** applies"
expect_fail "not applying stack precedents in Step 1 fails" "$work/noprecedentload" "Step 1 — Codebase Investigation is missing: unless that precedent's **Exception:** applies"

make_copy "$work/nostep2filter"
drop_lines "$work/nostep2filter/SKILL.md" '**Do Not Report and stack precedents**'
expect_fail "not refuting matches in Step 2 fails" "$work/nostep2filter" "Step 2 — Verify Findings is missing: **Do Not Report and stack precedents**"

# drop_from <file> <line>: removes the line equal to <line> and everything after it.
drop_from() {
  python3 - "$1" "$2" <<'PY'
import sys
path, line = sys.argv[1:]
lines = open(path, encoding="utf-8").read().splitlines()
open(path, "w", encoding="utf-8").write("\n".join(lines[:lines.index(line)]) + "\n")
PY
}

make_copy "$work/noprecedents"
drop_from "$work/noprecedents/stacks/go.md" '## Precedents'
expect_fail "a stack without Precedents fails" "$work/noprecedents" "stacks/go.md has no '## Precedents' section"

make_copy "$work/oneprecedent"
drop_lines "$work/oneprecedent/stacks/docker.md" '**Earlier build stages do not ship**'
expect_fail "a stack with one precedent fails" "$work/oneprecedent" "stacks/docker.md: '## Precedents' has 1 item(s), need 2 to 5"

make_copy "$work/toomany"
for i in 1 2 3 4; do
  printf -- '- **Extra %s**: Docker does this. Do not report that. **Exception:** never.\n' "$i" >> "$work/toomany/stacks/docker.md"
done
expect_fail "a stack with six precedents fails" "$work/toomany" "stacks/docker.md: '## Precedents' has 6 item(s), need 2 to 5"

make_copy "$work/noexception"
replace_first "$work/noexception/stacks/react.md" '**Exception:**' 'Except'
expect_fail "a precedent without its exception fails" "$work/noexception" "stacks/react.md: Precedents item does not match"

make_copy "$work/notlast"
printf '\n## Notes\n\n- note\n' >> "$work/notlast/stacks/kafka.md"
expect_fail "a section after Precedents fails" "$work/notlast" "stacks/kafka.md: '## Precedents' must be the last '## ' section"

if [ "$failures" -gt 0 ]; then
  printf '%d test(s) failed\n' "$failures"
  exit 1
fi
printf 'All negative tests passed\n'
