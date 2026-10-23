#!/usr/bin/env bash
# Verifies README counts, LICENSE, SKILL.md frontmatter, file references and output rules, and example-output.md.
# Usage: bash scripts/check-docs.sh   (exits 1 if any check fails)
set -u
cd "$(dirname "$0")/.." || exit 1

failures=0
pass() { printf 'PASS %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; failures=$((failures + 1)); }

check_license() {
  if [ -f LICENSE ] \
    && grep -qx 'MIT License' LICENSE \
    && grep -qx 'Copyright (c) 2026 Felipe Reis' LICENSE \
    && grep -qF 'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND' LICENSE; then
    pass "LICENSE is MIT, Copyright (c) 2026 Felipe Reis"
  else
    fail "LICENSE missing or not the standard MIT text for 2026 Felipe Reis"
  fi
}

check_frontmatter() {
  if python3 - <<'PY'
import re, sys
try:
    import yaml
except ImportError:
    print("  PyYAML is required: python3 -m pip install pyyaml")
    sys.exit(1)

text = open("SKILL.md", encoding="utf-8").read()
if not text.startswith("---\n"):
    print("  SKILL.md does not start with a --- fence")
    sys.exit(1)
try:
    fm = yaml.safe_load(text.split("---\n", 2)[1])
except yaml.YAMLError as exc:
    print(f"  frontmatter is not valid YAML: {exc}")
    sys.exit(1)

errors = []
allowed = {"name", "description", "license", "compatibility", "allowed-tools", "metadata"}
extra = sorted(set(fm) - allowed)
if extra:
    errors.append(f"unexpected top-level keys: {extra}")
if fm.get("name") != "code-review":
    errors.append("name must be code-review")
if fm.get("license") != "MIT":
    errors.append("license must be MIT")
desc = fm.get("description")
if not isinstance(desc, str) or not desc.strip():
    errors.append("description must be a non-empty string")
else:
    if len(desc) > 1024:
        errors.append(f"description is {len(desc)} chars (max 1024)")
    for trigger in ("review PR", "review my changes", "revisar minhas mudanças", "code review"):
        if trigger not in desc:
            errors.append(f"description missing trigger: {trigger}")
meta = fm.get("metadata")
if not isinstance(meta, dict):
    errors.append("metadata must be a mapping")
else:
    for key in ("author", "version", "date"):
        if key not in meta:
            errors.append(f"metadata.{key} missing")
    for key, value in meta.items():
        if not isinstance(value, str):
            errors.append(f"metadata.{key} must be a string, got {type(value).__name__}")
    if meta.get("version") != "2.0.0":
        errors.append("metadata.version must be 2.0.0")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(meta.get("date", ""))):
        errors.append("metadata.date must be YYYY-MM-DD")
for error in errors:
    print("  " + error)
sys.exit(1 if errors else 0)
PY
  then
    pass "SKILL.md frontmatter follows the Agent Skills spec"
  else
    fail "SKILL.md frontmatter (see messages above)"
  fi
}

check_readme_counts() {
  local stacks patterns scopes categories listed_patterns listed_categories missing="" f rc
  stacks=$(ls stacks/*.md | wc -l | tr -d ' ')
  patterns=$(ls patterns/*.md | wc -l | tr -d ' ')
  scopes=$(awk '/^## Step 0/{f=1; next} /^## /{f=0} f && /^[0-9]+\. \*\*/{n++} END{print n+0}' SKILL.md)
  categories=$(awk '/^## [0-9]+\. What Was Done Well/{exit} /^## [0-9]+\. /{n++} END{print n+0}' SKILL.md)
  listed_patterns=$(awk '/^## .*Architectural Patterns/{f=1; next} /^## /{f=0} f && /^- \*\*/{n++} END{print n+0}' README.md)
  listed_categories=$(awk '/^## .*Review Categories/{f=1; next} /^## /{f=0} f && /^\| \*\*/{n++} END{print n+0}' README.md)

  if grep -qF "**Multi-Stack Support** - ${stacks} technology stacks covered" README.md; then
    pass "README stack count matches stacks/ (${stacks})"
  else
    fail "README must say '**Multi-Stack Support** - ${stacks} technology stacks covered'"
  fi
  if grep -qF "**${scopes} Review Scopes**" README.md; then
    pass "README scope count matches SKILL.md Step 0 (${scopes})"
  else
    fail "README must say '**${scopes} Review Scopes**'"
  fi
  if grep -qF "**${categories} Review Categories**" README.md; then
    pass "README category count matches SKILL.md checklist sections (${categories})"
  else
    fail "README must say '**${categories} Review Categories**'"
  fi
  if [ "$listed_categories" = "$categories" ]; then
    pass "README Review Categories table has ${categories} rows"
  else
    fail "README Review Categories table has ${listed_categories} rows, SKILL.md has ${categories} checklist sections"
  fi
  if [ "$listed_patterns" = "$patterns" ]; then
    pass "README lists ${patterns} architectural patterns"
  else
    fail "README lists ${listed_patterns} architectural patterns, patterns/ has ${patterns}"
  fi
  git grep -nE '15 Review (Scopes|Categories)|19 (technology )?stacks' -- '*.md'; rc=$?
  if [ "$rc" -eq 1 ]; then
    pass "no stale '15 Review Scopes' / '15 Review Categories' / '19 stacks'"
  elif [ "$rc" -eq 0 ]; then
    fail "stale counts found (lines above)"
  else
    fail "git grep failed (run the script inside a git checkout)"
  fi
  for f in stacks/*.md patterns/*.md LICENSE example-output.md scripts/check-docs.sh scripts/test-check-docs.sh evals/run.py evals/score.py evals/make-patch.sh .github/workflows/ci.yml; do
    grep -qF "── ${f##*/}" README.md || missing="${missing} ${f}"
  done
  if [ -z "$missing" ]; then
    pass "README Project Structure lists every stack, pattern and top-level file"
  else
    fail "README Project Structure is missing:${missing}"
  fi
}

check_example_output() {
  if grep -qF 'select: { id: true, email: true }' example-output.md \
    && ! grep -qF 'password: true' example-output.md; then
    pass "example-output.md select matches its finding (no password)"
  else
    fail "example-output.md must suggest 'select: { id: true, email: true }' and no 'password: true'"
  fi
  if grep -nF '1.0.0' SKILL.md README.md example-output.md; then
    fail "stale version 1.0.0 found (lines above)"
  else
    pass "no stale version 1.0.0"
  fi
  if grep -qxF '*Generated by Code Review Skill v2.0.0*' example-output.md; then
    pass "example-output.md footer says v2.0.0"
  else
    fail "example-output.md footer must be '*Generated by Code Review Skill v2.0.0*'"
  fi
}

check_skill_references() {
  if python3 - <<'PY'
import glob, os, re, sys

text = open("SKILL.md", encoding="utf-8").read()
refs = []
for token in re.findall(r"`([^`\s]+)`", text):
    if (token.startswith("./") or token.endswith(".md")) and "://" not in token \
            and not any(c in token for c in "*<>{}$"):
        refs.append(token)
for target in re.findall(r"\]\(([^)\s]+)\)", text):
    target = target.split("#", 1)[0]
    if target and "://" not in target and not target.startswith("mailto:"):
        refs.append(target)
cited = sorted({os.path.normpath(r) for r in refs})
errors = []
if not cited:
    errors.append("no file references found in SKILL.md (extraction is broken)")
for path in cited:
    if not os.path.isfile(path):
        errors.append(f"SKILL.md cites missing file: {path}")
for path in sorted(glob.glob("stacks/*.md") + glob.glob("patterns/*.md")):
    if path not in cited:
        errors.append(f"{path} is not cited in SKILL.md")
for error in errors:
    print("  " + error)
sys.exit(1 if errors else 0)
PY
  then
    pass "SKILL.md cited files exist and every stacks/ and patterns/ file is cited"
  else
    fail "SKILL.md file references (see messages above)"
  fi
}

check_skill_output_rules() {
  local missing=0 s
  for s in \
    '## Severity Levels' \
    'is never above **Warning**' \
    'do work or queries that grow with data size' \
    '## Evidence and Confidence' \
    '**Location:** `path/to/file.ext:start-end`' \
    '**Deletion-only exception:**' \
    'same deletion-only exception' \
    '**Evidence:** Trigger → effect' \
    '**Confidence:** High' \
    '## Needs human verification' \
    'Low-confidence findings are never reported' \
    '### Compact mode' \
    '- path/to/file.ext:line: Severity: problem → fix'; do
    if ! grep -qF -- "$s" SKILL.md; then
      printf '  SKILL.md is missing: %s\n' "$s"
      missing=$((missing + 1))
    fi
  done
  if grep -qF '**File:**' SKILL.md; then
    printf '  SKILL.md still uses **File:** (use **Location:**)\n'
    missing=$((missing + 1))
  fi
  if [ "$missing" -eq 0 ]; then
    pass "SKILL.md defines severity caps, evidence, confidence and compact mode"
  else
    fail "SKILL.md severity, evidence and output-format rules (see messages above)"
  fi
}

check_skill_verification() {
  if python3 - <<'PY'
import sys

lines = open("SKILL.md", encoding="utf-8").read().splitlines()
heading = "## Step 2 — Verify Findings"
errors = []


def first(prefix):
    return next((i for i, line in enumerate(lines) if line.startswith(prefix)), None)


start = first(heading)
if start is None:
    errors.append(f"SKILL.md has no '{heading}' section")
else:
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    section = "\n".join(lines[start:end])
    last_check, report = first("## 13. "), first("## 14. What Was Done Well")
    if last_check is None or report is None or not last_check < start < report:
        errors.append(f"'{heading}' must come after '## 13.' and before '## 14. What Was Done Well'")
    for s in ("refute", "**CONFIRMED**", "**DOWNGRADED**", "**REFUTED**", "Suggestions skip this step",
              "**Confidence:** Medium", "name it in the Evidence", "**With subagents**", "**Without subagents**"):
        if s not in section:
            errors.append(f"Step 2 — Verify Findings is missing: {s}")
    for s in ("Task tool", "Agent tool", "subagent_type", "spawn_agent", "Claude", "Codex", "Cursor", "Copilot"):
        if s in section:
            errors.append(f"Step 2 — Verify Findings names an agent-specific tool: {s}")
output_start = first("## 15. Output Format")
output = "\n".join(lines[output_start:]) if output_start is not None else ""
for s in ("**Verification:** <checked> Critical/Warning candidates checked, <refuted> refuted.",
          "Do not list refuted findings unless the user asks for them.",
          "but end with the verification line"):
    if s not in output:
        errors.append(f"Output Format is missing: {s}")
for error in errors:
    print("  " + error)
sys.exit(1 if errors else 0)
PY
  then
    pass "SKILL.md Step 2 verifies Critical/Warning findings before the report"
  else
    fail "SKILL.md verification step (see messages above)"
  fi
}

check_skill_do_not_report() {
  if python3 - <<'PY'
import sys

lines = open("SKILL.md", encoding="utf-8").read().splitlines()
heading = "## Do Not Report"
errors = []


def first(prefix):
    return next((i for i, line in enumerate(lines) if line.startswith(prefix)), None)


def section(start):
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


start = first(heading)
evidence = first("## Evidence and Confidence")
step1 = first("## Step 1 — Codebase Investigation")
step2 = first("## Step 2 — Verify Findings")
if start is None:
    errors.append(f"SKILL.md has no '{heading}' section")
else:
    if evidence is None or step1 is None or not evidence < start < step1:
        errors.append(f"'{heading}' must come after '## Evidence and Confidence' and before "
                      "'## Step 1 — Codebase Investigation'")
    body = section(start)
    text = "\n".join(body)
    for s in ("**Pre-existing problems**", "**What tooling already catches**", "**Silenced rules**",
              "**Style and naming nits**", "**Theoretical denial of service**",
              '**"Verify" or "ensure" without a scenario**', "**Generic hardening**",
              "When a changed line triggers a problem in old code, report it",
              "counts as refuted on the verification line", "dropped without being counted",
              "Do not move a matching finding to `## Needs human verification`", "`## Precedents`"):
        if s not in text:
            errors.append(f"Do Not Report is missing: {s}")
    for line in body:
        if line.startswith("- **") and " Why: " not in line:
            errors.append("Do Not Report item has no 'Why:': " + line.split("**")[1])
s = "unless that precedent's **Exception:** applies"
if step1 is not None and s not in "\n".join(section(step1)):
    errors.append(f"Step 1 — Codebase Investigation is missing: {s}")
s = "**Do Not Report and stack precedents**"
if step2 is not None and s not in "\n".join(section(step2)):
    errors.append(f"Step 2 — Verify Findings is missing: {s}")
for error in errors:
    print("  " + error)
sys.exit(1 if errors else 0)
PY
  then
    pass "SKILL.md Do Not Report list is complete and applied in Step 1 and Step 2"
  else
    fail "SKILL.md Do Not Report list (see messages above)"
  fi
}

check_example_findings() {
  if python3 - <<'PY'
import re, sys
sys.path.insert(0, "evals")
from score import parse_findings

text = open("example-output.md", encoding="utf-8").read()
findings = parse_findings(text)
full = [f for f in findings if not f["compact"]]
compact = [f for f in findings if f["compact"]]
main = [f for f in full if not f["needs_verification"]]
verify = [f for f in full if f["needs_verification"]]
errors = []
if not main:
    errors.append("example-output.md has no finding under ## Findings")
if not verify:
    errors.append("example-output.md has no finding under ## Needs human verification")
if not compact:
    errors.append("example-output.md has no compact-mode lines")
for f in full:
    if not re.search(r"^\*\*Location:\*\* `[^`\s]+:\d+(-\d+)?`$", f["text"], re.M):
        errors.append(f"finding '{f['heading']}' needs a **Location:** `path:start-end` line")
    for field in ("Issue", "Evidence", "Confidence", "Fix"):
        if not re.search(r"^\*\*" + field + r":\*\* \S", f["text"], re.M):
            errors.append(f"finding '{f['heading']}' has no **{field}:** line")
    expected = "Medium" if f["needs_verification"] else "High"
    if not re.search(r"^\*\*Confidence:\*\* " + expected + "$", f["text"], re.M):
        errors.append(f"finding '{f['heading']}' must have **Confidence:** {expected}")
if re.search(r"^\*\*File:\*\*", text, re.M):
    errors.append("example-output.md still uses **File:** lines")
if re.search(r"^\*\*Confidence:\*\* Low", text, re.M):
    errors.append("example-output.md reports a Low-confidence finding")
counts = [sum(f["severity"] == s for f in main) for s in ("Critical", "Warning", "Suggestion")]
total = re.search(r"^\| \*\*Total\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \|", text, re.M)
if total is None:
    errors.append("example-output.md Summary has no | **Total** | row")
elif [int(n) for n in total.groups()] != counts:
    errors.append(f"Summary Total row is {[int(n) for n in total.groups()]} but ## Findings has "
                  f"Critical/Warning/Suggestion {counts}")
def severities(items):
    return sorted(f["severity"] for f in items)
if severities(f for f in compact if not f["needs_verification"]) != severities(main):
    errors.append("compact-mode lines must have the same severities as ## Findings")
if severities(f for f in compact if f["needs_verification"]) != severities(verify):
    errors.append("compact-mode Needs human verification lines must match the full report")
verify_lines = list(re.finditer(
    r"^\*\*Verification:\*\* (\d+) Critical/Warning candidates checked, (\d+) refuted\.$", text, re.M))
if len(verify_lines) != 2:
    errors.append("example-output.md must have 2 **Verification:** lines (full report and compact mode), "
                  f"found {len(verify_lines)}")
else:
    full_line, compact_line = verify_lines
    checked, refuted = int(full_line.group(1)), int(full_line.group(2))
    if full_line.groups() != compact_line.groups():
        errors.append("the full-report and compact-mode **Verification:** lines must match")
    if total is not None and full_line.start() < total.start():
        errors.append("the full-report **Verification:** line must come after the Summary table")
    if refuted < 1:
        errors.append("the example **Verification:** line must show at least 1 refuted candidate")
    kept = sum(f["severity"] in ("Critical", "Warning") for f in full)
    if checked - refuted < kept:
        errors.append(f"**Verification:** leaves {checked - refuted} unrefuted candidates but the full report "
                      f"has {kept} Critical/Warning findings")
if not any("Verification checked" in f["text"] for f in full):
    errors.append("no example finding's Evidence names what verification checked ('Verification checked ...')")
for error in errors:
    print("  " + error)
sys.exit(1 if errors else 0)
PY
  then
    pass "example-output.md findings carry Location, Evidence and Confidence and match the Summary and the Verification line"
  else
    fail "example-output.md findings (see messages above)"
  fi
}

# --- run checks ---
check_license
check_frontmatter
check_skill_references
check_skill_output_rules
check_skill_verification
check_skill_do_not_report
check_readme_counts
check_example_output
check_example_findings

if [ "$failures" -gt 0 ]; then
  printf '%d check(s) failed\n' "$failures"
  exit 1
fi
printf 'All checks passed\n'
