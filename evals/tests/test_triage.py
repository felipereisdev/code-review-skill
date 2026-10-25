"""Offline checks of the triage, verdict and audit contract in SKILL.md Step 3 against handwritten reports; they do not measure what an agent writes."""
from __future__ import annotations

import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import run  # noqa: E402
from score import looks_like_report, parse_findings, score_bug, score_clean  # noqa: E402

CATEGORIES = ("Security", "Performance", "Tests/Coverage", "Architecture", "Code & File Size", "Potential Bugs",
              "Accessibility", "Observability", "API Design", "Resilience", "DB Migrations", "Concurrency", "i18n",
              "Privacy/Compliance", "Architecture Patterns", "Stack-Specific")
TRIAGE = ("Review effort", "Relevant tests", "Look first", "Ready to merge")
TAGS = ("not read", "binary", "context not read", "API not validated", "tests not verified")
WEIGHTS = ("material", "not material")
LINE_RES = {
    "Review effort": re.compile(r"^\*\*Review effort:\*\* ([1-5])/5 — \d+ changed lines? in (\d+) files?; \S.*\.$"),
    "Relevant tests": re.compile(
        r"^\*\*Relevant tests:\*\* (changed|existing|missing|not applicable|not verified) — (\S.*?)\. "
        r"Execution: (not run|ran `[^`]+`(?:, `[^`]+`)*; \S.*|partly ran `[^`]+`(?:, `[^`]+`)*; \S.*; not run: \S.*)\.$"),
    "Look first": re.compile(r"^\*\*Look first:\*\* (?:no reviewed file|`[^`]+` \([^)]+\)(?:, `[^`]+` \([^)]+\)){0,2})\.$"),
    "Ready to merge": re.compile(r"^\*\*Ready to merge:\*\* (?:Yes|No|With fixes) — \S.*\.$"),
}
RESULT_RE = re.compile(r"(?i)(?:\b(?:tests?|suites?|specs?)\b|`[^`]*(?:test|spec)[^`]*`)\s+(?:all\s+)?(?:pass(?:es|ed)?|fail(?:s|ed)?)\b")
ITEM_RE = re.compile(r"^- (.+?) — (not read|binary|context not read|API not validated|tests not verified), (material|not material): (\S.*)$")
COMPACT_AUDIT = re.compile(r"^\*\*Audit:\*\* (\d+) of (\d+) changed files? reviewed; (\d+) files? read for context; no findings in (.+?); (?:already raised, not verified: (\d+) Warning candidates?; )?not verified: (.+)\.$")
FILES_RE = re.compile(r"^\*\*Files reviewed:\*\* (\d+) of (\d+) changed files?(?:: (.+))?\.$")
CONTEXT_RE = re.compile(r"^\*\*Read for context:\*\* (?:none|(\d+) files?: (.+))\.$")
CLEAN_RE = re.compile(r"^\*\*Checked with no findings:\*\* (.+)\.$")
RAISED_RE = re.compile(r"^\*\*Already raised, not verified:\*\* (.+)\.$")
RAISED_ENTRY_RE = re.compile(r"`([^`]+)` \(([^)]+)\)")
EXCLUDED_RE = re.compile(r"^\*\*Excluded by configuration:\*\* (\d+) changed files?\b")
RAISED_HEADING = "## Already raised in the PR (not repeated)"

FINDING_BLOCKS = ("### Security — Critical", "### Potential Bugs — Warning", "### Performance — Warning")
API_ITEM = ("- `pg` query options in `src/orders.js` — API not validated, not material: no documentation tool was "
            "available; no changed behavior depends on these options.")
API_MATERIAL = ("- `pg` query options in `src/orders.js` — API not validated, material: no documentation tool was "
                "available, and the order of the changed query's rows depends on these options.")
TNV_ITEM = "- relevant tests — tests not verified, not material: `tests/orders.test.js` could not be opened."
CHECKED = "**Checked with no findings:** Architecture, Code & File Size."
ALREADY = "**Already raised, not verified:** `src/orders.js:40` (Potential Bugs)."
COMPACT_FIXTURE = ("**Audit:** 2 of 2 changed files reviewed; 2 files read for context; no findings in Architecture, "
                   "Code & File Size; not verified: `pg` query options in `src/orders.js` (API not validated, not material).")
L = ("`src/a.js` lines 10-90", "not read")
W = ("`src/pay.js` (whole file)", "not read")
C = ("gateway configuration", "context not read")
A = ("`pg` query options in `src/orders.js`", "API not validated")
CTX = ("`chargeCard` in the payments service", "context not read")
MATERIAL_CONTEXT = ("- `chargeCard` in the payments service — context not read, material: the head commit is not in this "
                    "repository, and whether the changed call passes the amount in cents depends on its contract.")


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


FIXTURE = read("fixtures/triage/report.md")
EXAMPLE = read(os.path.join("..", "..", "example-output.md"))
REPORT_END = "The report ends with the Audit above."
CRITICAL_VERDICT = ("**Ready to merge:** No — 2 Critical findings must be fixed before merging. "
                    "Not fully reviewed: see the Audit.")


def example_full():
    return EXAMPLE[EXAMPLE.index("## Code Review Report"):EXAMPLE.index(REPORT_END)]


def plural(n, word):
    return f"{n} {word}" + ("s" if n != 1 else "")


def verdict_line(*, reviewed=1, critical=0, warning=0, needs=0, raised=0, material=(),
                 omitted_warning=0, omitted_needs=0, excluded=0):
    """The **Ready to merge:** line of SKILL.md Step 3; every count is taken before the configuration filters."""
    def omitted(k):
        return f" ({k} omitted by configuration)" if k else ""
    if reviewed == 0:
        text = "No — not fully reviewed: no changed file was reviewed."
    elif critical:
        text = f"No — {plural(critical, 'Critical finding')} must be fixed before merging."
        if material:
            text += " Not fully reviewed: see the Audit."
    elif material:
        what, tag = material[0]
        text = f"No — not fully reviewed ({tag}): {what}."
        more = len(material) - 1
        if more:
            text += f" {plural(more, 'more material limit')} {'is' if more == 1 else 'are'} in the Audit."
    elif warning:
        text = (f"With fixes — {plural(warning, 'Warning finding')}{omitted(omitted_warning)} "
                "should be fixed; none blocks the merge.")
    elif needs:
        text = (f"With fixes — a person must check {plural(needs, 'finding')}{omitted(omitted_needs)} "
                "under Needs human verification before merging.")
    elif raised:
        text = (f"With fixes — {plural(raised, 'Warning candidate')} already raised in "
                f"{'an open thread still needs' if raised == 1 else 'open threads still need'} "
                "verification before merging.")
    else:
        text = "Yes — no Critical or Warning findings."
    if excluded:
        text += (f" {plural(excluded, 'changed file')} excluded by configuration "
                 f"{'was' if excluded == 1 else 'were'} not reviewed.")
    return "**Ready to merge:** " + text


def effort_level(changed_lines, risk_areas):
    """The Review effort score of SKILL.md Step 3: a size band plus up to two risk areas, capped at 5."""
    if changed_lines <= 50:
        base = 1
    elif changed_lines <= 200:
        base = 2
    elif changed_lines <= 500:
        base = 3
    elif changed_lines <= 1000:
        base = 4
    else:
        base = 5
    return min(base + min(risk_areas, 2), 5)


def find_line(lines, prefix):
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            return i
    return None


def line_of(text, label):
    prefix = f"**{label}:**"
    for line in text.split("\n"):
        if line.startswith(prefix):
            return line
    raise AssertionError(f"no {label} line")


def triage_lines(text):
    """The first line of each triage label, in TRIAGE order; None when the label is absent."""
    lines = text.split("\n")
    result = []
    for label in TRIAGE:
        i = find_line(lines, f"**{label}:** ")
        result.append(lines[i] if i is not None else None)
    return result


def parse_paths(text, message):
    """A path list is backticked paths joined by ', ' and nothing else; no list (None) names no path."""
    if text is None:
        return []
    paths = re.findall(r"`([^`]+)`", text)
    if ", ".join(f"`{p}`" for p in paths) != text:
        raise ValueError(message)
    return paths


def audit_lines(text):
    lines = text.split("\n")
    if "## Audit" not in lines:
        raise ValueError("## Audit is missing")
    body = []
    for line in lines[lines.index("## Audit") + 1:]:
        if line.startswith("#") or line == "---":
            break
        if line.strip():
            body.append(line)
    return body


def parse_audit(text):
    """Read the Audit section into counts, path lists and limit items; ValueError names the first malformed line."""
    body = audit_lines(text)
    line = body.pop(0) if body else ""
    files = FILES_RE.match(line)
    if not files:
        raise ValueError("**Files reviewed:** line is malformed")
    paths = parse_paths(files.group(3), "**Files reviewed:** line is malformed")

    line = body.pop(0) if body else ""
    context_match = CONTEXT_RE.match(line)
    if not context_match:
        raise ValueError("**Read for context:** line is malformed")
    context = parse_paths(context_match.group(2), "**Read for context:** line is malformed")

    line = body.pop(0) if body else ""
    clean_match = CLEAN_RE.match(line)
    if not clean_match:
        raise ValueError("**Checked with no findings:** line is malformed")
    clean = [] if clean_match.group(1) == "none" else clean_match.group(1).split(", ")

    raised = None
    if body and body[0].startswith("**Already raised, not verified:**"):
        line = body.pop(0)
        raised_match = RAISED_RE.match(line)
        if not raised_match:
            raise ValueError("**Already raised, not verified:** line is malformed")
        if raised_match.group(1) == "none":
            raised = []
        else:
            raised = RAISED_ENTRY_RE.findall(raised_match.group(1))
            if ", ".join(f"`{loc}` ({cat})" for loc, cat in raised) != raised_match.group(1):
                raise ValueError("**Already raised, not verified:** line is malformed")

    line = body.pop(0) if body else ""
    items = []
    if line == "**Not verified:** nothing.":
        pass
    elif line == "**Not verified:**":
        while body and body[0].startswith("- "):
            entry = body.pop(0)
            item = ITEM_RE.match(entry)
            if not item:
                raise ValueError(f"Not verified item is malformed: {entry}")
            items.append(item.groups())
    else:
        raise ValueError("**Not verified:** line is missing")
    if body:
        raise ValueError(f"## Audit has an unexpected line: {body[0]}")

    return {
        "reviewed": int(files.group(1)),
        "changed": int(files.group(2)),
        "paths": paths,
        "context": context,
        "context_count": int(context_match.group(1) or 0),
        "clean": clean,
        "raised": raised,
        "items": items,
    }


def compact_audit_line(audit):
    clean = ", ".join(audit["clean"])
    raised = audit["raised"]
    raised_part = (f"already raised, not verified: {plural(len(raised), 'Warning candidate')}; "
                   if raised is not None else "")
    items = ", ".join(f"{what} ({tag}, {weight})" for what, tag, weight, _detail in audit["items"])
    return (f"**Audit:** {audit['reviewed']} of {plural(audit['changed'], 'changed file')} reviewed; "
            f"{plural(audit['context_count'], 'file')} read for context; "
            f"no findings in {clean or 'no category'}; {raised_part}not verified: {items or 'nothing'}.")


def raised_locations(lines):
    if RAISED_HEADING not in lines:
        return set()
    locations = set()
    for line in lines[lines.index(RAISED_HEADING) + 1:]:
        if line.startswith("#"):
            break
        m = re.match(r"^- (\S+) — ", line)
        if m:
            locations.add(m.group(1))
    return locations


def _check_files(audit, excluded):
    reviewed, changed, paths = audit["reviewed"], audit["changed"], audit["paths"]
    context = audit["context"]
    errors = []
    if reviewed > changed:
        errors.append("Files reviewed counts more files than changed")
    if len(paths) != reviewed:
        errors.append(f"Files reviewed lists {len(paths)} paths but counts {reviewed}")
    if paths != sorted(set(paths)):
        errors.append("Files reviewed paths must be unique and in alphabetical order")
    if len(context) != audit["context_count"]:
        errors.append(f"Read for context lists {len(context)} paths but counts {audit['context_count']}")
    if context != sorted(set(context)):
        errors.append("Read for context paths must be unique and in alphabetical order")
    unread = [item for item in audit["items"] if item[1] == "not read" and item[0].endswith(" (whole file)")]
    binary = [item for item in audit["items"] if item[1] == "binary"]
    for what, tag, _weight, _detail in unread + binary:
        m = re.search(r"`([^`]+)`", what)
        if m and m.group(1) in paths:
            errors.append(f"Files reviewed lists `{m.group(1)}`, which the Audit also lists as {tag}")
    u, b = len(unread), len(binary)
    if reviewed + excluded + b + u != changed:
        errors.append(f"Files reviewed: {reviewed} reviewed, {excluded} excluded, {b} binary and {u} not read "
                      f"do not add up to {changed} changed files")
    return errors


def _check_clean(audit, finding_categories, tests_not_verified):
    raised_categories = {cat for _loc, cat in audit["raised"] or []}
    errors = []
    for cat in audit["clean"]:
        if cat not in CATEGORIES:
            errors.append(f"Checked with no findings names unknown category {cat}")
            continue
        if cat in finding_categories:
            errors.append(f"Checked with no findings names {cat}, which has a finding")
        if cat in raised_categories:
            errors.append(f"Checked with no findings names {cat}, which has a Warning candidate already raised")
        if cat == "Tests/Coverage" and tests_not_verified:
            errors.append("Checked with no findings names Tests/Coverage, but the relevant tests were not verified")
    order = [CATEGORIES.index(cat) for cat in audit["clean"] if cat in CATEGORIES]
    if order != sorted(order):
        errors.append("Checked with no findings must follow the Summary table order")
    return errors


def _check_raised(audit, is_pr, lines):
    raised = audit["raised"]
    errors = []
    if is_pr and raised is None:
        errors.append("**Already raised, not verified:** line is missing in a pr review")
    if not is_pr and raised is not None:
        errors.append("**Already raised, not verified:** line is only for a pr review")
    locations = raised_locations(lines)
    for loc, cat in raised or []:
        if loc not in locations:
            errors.append(f"Already raised, not verified names {loc}, which is not under Already raised in the PR")
        if cat not in CATEGORIES:
            errors.append(f"Already raised, not verified names unknown category {cat}")
    return errors


def _check_triage(triage, audit, excluded, tests_not_verified):
    errors = []
    paths, reviewed = audit["paths"], audit["reviewed"]
    look = triage["Look first"]
    if look.startswith("**Look first:** no reviewed file"):
        if reviewed > 0:
            errors.append(f"**Look first:** names no file, but {reviewed} files were reviewed")
    else:
        for path in re.findall(r"`([^`]+)` \(", look):
            if path not in paths:
                errors.append(f"Look first names {path}, which is not a reviewed file")

    effort = LINE_RES["Review effort"].match(triage["Review effort"])
    if effort and int(effort.group(2)) != audit["changed"] - excluded:
        errors.append(f"Review effort counts {effort.group(2)} files, but {audit['changed'] - excluded} "
                      "changed files are not excluded by configuration")

    relevant = LINE_RES["Relevant tests"].match(triage["Relevant tests"])
    if relevant:
        status = relevant.group(1)
        if status == "not verified" and not tests_not_verified:
            errors.append("**Relevant tests:** is not verified, but the Audit has no tests not verified item")
        if tests_not_verified and status != "not verified":
            errors.append(f"the Audit has a tests not verified item, but **Relevant tests:** is {status}")
    return errors


def check_report(text, *, omitted_warning=0, omitted_needs=0):
    """Return the consistency errors of a canonical report; [] when its triage, Audit and findings agree."""
    errors = []
    lines = text.split("\n")
    findings = [f for f in parse_findings(text) if not (f["compact"] or f["pre_existing"] or f["already_raised"])]
    main = [f for f in findings if not f["needs_verification"]]
    needs = [f for f in findings if f["needs_verification"]]
    critical = sum(f["severity"] == "Critical" for f in main)
    warning = sum(f["severity"] == "Warning" for f in main) + omitted_warning
    needs_count = sum(f["severity"] in ("Critical", "Warning") for f in needs) + omitted_needs
    finding_categories = {f["heading"].split(" — ")[0] for f in findings}

    at = {label: find_line(lines, f"**{label}:** ") for label in TRIAGE}
    triage = {label: (lines[at[label]] if at[label] is not None else "") for label in TRIAGE}
    for label in TRIAGE:
        if at[label] is None:
            errors.append(f"missing **{label}:** line")
        elif not LINE_RES[label].match(triage[label]):
            errors.append(f"**{label}:** line does not match its form")
    found = [at[label] for label in TRIAGE if at[label] is not None]
    if len(found) == len(TRIAGE) and found != list(range(found[0], found[0] + len(TRIAGE))):
        errors.append("triage lines are not consecutive in the order Review effort, Relevant tests, "
                      "Look first, Ready to merge")
    verification = find_line(lines, "**Verification:**")
    if verification is not None and found and min(found) < verification:
        errors.append("triage lines must come after the verification line")

    relevant = LINE_RES["Relevant tests"].match(triage["Relevant tests"])
    if relevant and relevant.group(3) == "not run" and RESULT_RE.search(relevant.group(2)):
        errors.append("**Relevant tests:** claims a test result, but Execution is not run")

    excluded = 0
    for line in lines:
        m = EXCLUDED_RE.match(line)
        if m:
            excluded = int(m.group(1))
            break

    audit_at = lines.index("## Audit") if "## Audit" in lines else None
    if audit_at is not None:
        if at["Ready to merge"] is not None and audit_at < at["Ready to merge"]:
            errors.append("## Audit must come after the triage lines")
        if any(line.startswith("#") for line in lines[audit_at + 1:]):
            errors.append("## Audit must be the last section of the report")

    try:
        audit = parse_audit(text)
    except ValueError as error:
        return errors + [str(error)]

    scope = find_line(lines, "**Scope:**")
    is_pr = scope is not None and lines[scope].startswith("**Scope:** pr ")
    items = audit["items"]
    tests_not_verified = any(tag == "tests not verified" for _what, tag, _weight, _detail in items)

    errors += _check_files(audit, excluded)
    errors += _check_clean(audit, finding_categories, tests_not_verified)
    errors += _check_raised(audit, is_pr, lines)
    errors += _check_triage(triage, audit, excluded, tests_not_verified)

    want = verdict_line(
        reviewed=audit["reviewed"], critical=critical, warning=warning, needs=needs_count,
        raised=len(audit["raised"] or []),
        material=[(what, tag) for what, tag, weight, _detail in items if weight == "material"],
        omitted_warning=omitted_warning, omitted_needs=omitted_needs, excluded=excluded)
    got = triage["Ready to merge"]
    if got and got != want:
        errors.append(f"Ready to merge line is {got!r}, expected {want!r}")
    return errors


def check_summary_triage(body, report, compact_line):
    """Errors for a published summary that lacks the report's triage lines or its compact Audit line."""
    errors = []
    lines = body.split("\n")
    expected = [line for line in triage_lines(report) if line is not None]
    for line in expected:
        if line not in lines:
            errors.append(f"summary misses the triage line: {line}")
    if compact_line not in lines:
        errors.append("summary misses the audit line")
    present = [lines.index(line) for line in expected if line in lines]
    verification = find_line(lines, "**Verification:**")
    if verification is not None and present and min(present) < verification:
        errors.append("summary triage lines must follow the verification line")
    ready = find_line(lines, "**Ready to merge:**")
    if compact_line in lines and ready is not None and lines.index(compact_line) < ready:
        errors.append("summary audit line must follow the triage lines")
    return errors


def inline_has_triage(body):
    return any(f"**{label}:**" in body for label in (*TRIAGE, "Audit"))


def drop_block(text, heading):
    """Remove the heading line and the lines under it, up to the next heading."""
    out, skipping = [], False
    for line in text.split("\n"):
        if line == heading:
            skipping = True
            continue
        if skipping and line.startswith("#"):
            skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out)


def drop_heading(text, line):
    return "\n".join(x for x in text.split("\n") if x != line)


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def set_line(text, label, line):
    return replace_once(text, line_of(text, label), line)


def with_items(text, *lines):
    return replace_once(text, API_ITEM, "\n".join(lines))


def with_verdict(text, **kwargs):
    return set_line(text, "Ready to merge", verdict_line(**kwargs))


def no_findings(text):
    for heading in FINDING_BLOCKS:
        text = drop_block(text, heading)
    return text


def as_pr(text):
    text = set_line(text, "Scope", "**Scope:** pr 7 (gh pr diff 7)")
    text = replace_once(text, "## Summary\n", RAISED_HEADING + "\n\n"
                        "- src/orders.js:40 — the export skips cancelled orders "
                        "(https://github.com/acme/shop/pull/7#discussion_r1)\n\n## Summary\n")
    return replace_once(text, CHECKED + "\n", CHECKED + "\n" + ALREADY + "\n")


def wide(text, listed):
    """A 25-file change whose Files reviewed line lists the first `listed` paths."""
    paths = ", ".join(f"`src/f{i:02d}.js`" for i in range(listed))
    text = set_line(text, "Files reviewed", f"**Files reviewed:** 25 of 25 changed files: {paths}.")
    text = set_line(text, "Review effort", "**Review effort:** 3/5 — 300 changed lines in 25 files; payments.")
    return set_line(text, "Look first", "**Look first:** `src/f00.js` (the largest change).")


def triage_block(text):
    return "\n".join(line for line in triage_lines(text) if line is not None)


class Base(unittest.TestCase):
    def assertError(self, errors, text):
        self.assertTrue(any(text in error for error in errors), errors)


class ReportTests(Base):
    def test_fixture_is_consistent(self):
        self.assertEqual(check_report(FIXTURE), [])

    def test_yes_with_a_critical_finding_fails(self):
        text = set_line(FIXTURE, "Ready to merge", verdict_line())
        self.assertError(check_report(text), "Ready to merge line is")

    def test_warning_only_is_with_fixes(self):
        text = drop_block(FIXTURE, FINDING_BLOCKS[0])
        self.assertEqual(check_report(with_verdict(text, warning=1)), [])
        self.assertError(check_report(text), "Ready to merge line is")

    def test_needs_verification_only_is_with_fixes(self):
        text = drop_block(drop_block(FIXTURE, FINDING_BLOCKS[0]), FINDING_BLOCKS[1])
        self.assertEqual(check_report(with_verdict(text, needs=1)), [])

    def test_omitted_warning_still_counts(self):
        text = with_verdict(no_findings(FIXTURE), warning=1, omitted_warning=1)
        self.assertEqual(check_report(text, omitted_warning=1), [])
        self.assertError(check_report(text), "Ready to merge line is")

    def test_omitted_needs_still_counts(self):
        text = drop_block(drop_block(FIXTURE, FINDING_BLOCKS[0]), FINDING_BLOCKS[1])
        literal = ("**Ready to merge:** With fixes — a person must check 2 findings (1 omitted by configuration) "
                   "under Needs human verification before merging.")
        text = set_line(text, "Ready to merge", literal)
        self.assertEqual(literal, verdict_line(needs=2, omitted_needs=1))
        self.assertEqual(check_report(text, omitted_needs=1), [])
        self.assertError(check_report(text), "Ready to merge line is")
        wrong = set_line(text, "Ready to merge", "**Ready to merge:** With fixes — a person must check 2 findings "
                         "under Needs human verification (1 omitted by configuration) before merging.")
        self.assertError(check_report(wrong, omitted_needs=1), "Ready to merge line is")

    def test_nothing_reviewed_is_never_yes(self):
        text = no_findings(FIXTURE)
        text = set_line(text, "Files reviewed", "**Files reviewed:** 0 of 2 changed files.")
        text = set_line(text, "Checked with no findings", "**Checked with no findings:** none.")
        text = set_line(text, "Look first", "**Look first:** no reviewed file.")
        text = set_line(text, "Relevant tests", "**Relevant tests:** not verified — no changed file could be read. "
                        "Execution: not run.")
        text = with_items(
            text,
            "- `src/orders.js` (whole file) — not read, material: it could not be opened.",
            "- `src/routes.js` (whole file) — not read, material: it could not be opened.",
            "- relevant tests — tests not verified, not material: no changed file could be read.")
        self.assertError(check_report(set_line(text, "Ready to merge", verdict_line())), "Ready to merge line is")
        self.assertEqual(check_report(with_verdict(text, reviewed=0)), [])

    def test_material_lines_not_read_block(self):
        text = with_items(no_findings(FIXTURE), "- `src/routes.js` lines 40-90 — not read, material: "
                          "the diff output was cut off.")
        material = [("`src/routes.js` lines 40-90", "not read")]
        self.assertEqual(check_report(with_verdict(text, material=material)), [])
        self.assertError(check_report(with_verdict(text)), "Ready to merge line is")

    def test_material_limit_with_critical_adds_suffix(self):
        text = with_items(FIXTURE, "- `src/routes.js` lines 40-90 — not read, material: the diff output was cut off.")
        self.assertEqual(check_report(with_verdict(text, critical=1, material=[("`src/routes.js` lines 40-90",
                                                                                "not read")])), [])

    def test_whole_unread_file_material_blocks(self):
        text = with_items(no_findings(FIXTURE),
                          "- `src/payments.js` (whole file) — not read, material: it could not be opened.")
        text = set_line(text, "Files reviewed", "**Files reviewed:** 2 of 3 changed files: `src/orders.js`, "
                        "`src/routes.js`.")
        text = set_line(text, "Review effort", "**Review effort:** 3/5 — 120 changed lines in 3 files; payments.")
        self.assertEqual(check_report(with_verdict(text, material=[("`src/payments.js` (whole file)", "not read")])),
                         [])

    def test_whole_unread_file_nonmaterial_does_not_block(self):
        text = with_items(no_findings(FIXTURE), "- `CHANGELOG.md` (whole file) — not read, not material: the diff "
                          "output was cut off before it; it holds release notes, not code.")
        text = set_line(text, "Files reviewed", "**Files reviewed:** 2 of 3 changed files: `src/orders.js`, "
                        "`src/routes.js`.")
        text = set_line(text, "Review effort", "**Review effort:** 3/5 — 120 changed lines in 3 files; payments.")
        self.assertEqual(check_report(with_verdict(text)), [])

    def test_unread_file_listed_as_reviewed_fails(self):
        text = with_items(no_findings(FIXTURE),
                          "- `src/routes.js` (whole file) — not read, material: it could not be opened.")
        text = set_line(text, "Files reviewed", "**Files reviewed:** 2 of 3 changed files: `src/orders.js`, "
                        "`src/routes.js`.")
        text = set_line(text, "Review effort", "**Review effort:** 3/5 — 120 changed lines in 3 files; payments.")
        self.assertError(check_report(text), "Files reviewed lists `src/routes.js`, which the Audit also lists as "
                         "not read")

    def test_file_accounting(self):
        text = set_line(FIXTURE, "Files reviewed", "**Files reviewed:** 2 of 3 changed files: `src/orders.js`, "
                        "`src/routes.js`.")
        text = set_line(text, "Review effort", "**Review effort:** 3/5 — 120 changed lines in 3 files; payments.")
        self.assertError(check_report(text), "do not add up to 3 changed files")

    def test_material_context_blocks(self):
        text = with_items(no_findings(FIXTURE), MATERIAL_CONTEXT)
        self.assertEqual(check_report(with_verdict(text, material=[CTX])), [])
        self.assertError(check_report(with_verdict(text)), "Ready to merge line is")

    def test_nonmaterial_context_does_not_block(self):
        text = with_items(no_findings(FIXTURE), "- gateway configuration — context not read, not material: it is not "
                          "in the repository; no changed line depends on it.")
        self.assertEqual(check_report(with_verdict(text)), [])

    def test_material_api_blocks(self):
        text = with_items(no_findings(FIXTURE), API_MATERIAL)
        self.assertEqual(check_report(with_verdict(text, material=[A])), [])

    def test_nonmaterial_api_does_not_block(self):
        self.assertEqual(check_report(with_verdict(no_findings(FIXTURE))), [])

    def test_material_binary_blocks(self):
        text = no_findings(FIXTURE)
        text = set_line(text, "Files reviewed", "**Files reviewed:** 2 of 3 changed files: `src/orders.js`, "
                        "`src/routes.js`.")
        text = set_line(text, "Review effort", "**Review effort:** 3/5 — 120 changed lines in 3 files; payments.")
        text = with_items(text, "- `lib/pricing.wasm` — binary, material: the changed prices are computed in this "
                          "compiled module.")
        self.assertEqual(check_report(with_verdict(text, material=[("`lib/pricing.wasm`", "binary")])), [])

    def test_nonmaterial_binary_does_not_block(self):
        text = no_findings(FIXTURE)
        text = set_line(text, "Files reviewed", "**Files reviewed:** 2 of 3 changed files: `src/orders.js`, "
                        "`src/routes.js`.")
        text = set_line(text, "Review effort", "**Review effort:** 3/5 — 120 changed lines in 3 files; payments.")
        text = with_items(text, "- `assets/logo.png` — binary, not material: a changed image that no changed code reads.")
        self.assertEqual(check_report(with_verdict(text)), [])

    def test_material_limit_beats_needs_verification(self):
        text = drop_block(drop_block(FIXTURE, FINDING_BLOCKS[0]), FINDING_BLOCKS[1])
        text = with_items(text, API_MATERIAL)
        self.assertEqual(check_report(with_verdict(text, needs=1, material=[A])), [])
        self.assertTrue(verdict_line(needs=1, material=[A]).startswith(
            "**Ready to merge:** No — not fully reviewed (API not validated): "))

    def test_two_material_limits_name_the_first(self):
        text = with_items(no_findings(FIXTURE), "- `src/a.js` lines 10-90 — not read, material: the diff output was "
                          "cut off.", MATERIAL_CONTEXT)
        expected = verdict_line(material=[L, CTX])
        self.assertTrue(expected.endswith(" 1 more material limit is in the Audit."))
        self.assertEqual(check_report(set_line(text, "Ready to merge", expected)), [])

    def test_excluded_files_suffix(self):
        text = replace_once(FIXTURE, "**Scope:** staged (git diff --cached)\n",
                            "**Scope:** staged (git diff --cached)\n**Excluded by configuration:** 2 changed files match "
                            "ignore_paths and were not reviewed: `docs/a.md`, `docs/b.md`.\n")
        text = replace_once(text, "**Files reviewed:** 2 of 2", "**Files reviewed:** 2 of 4")
        self.assertEqual(check_report(with_verdict(text, critical=1, excluded=2)), [])

    def test_excluded_files_do_not_block(self):
        text = replace_once(no_findings(FIXTURE), "**Scope:** staged (git diff --cached)\n",
                            "**Scope:** staged (git diff --cached)\n**Excluded by configuration:** 2 changed files match "
                            "ignore_paths and were not reviewed: `docs/a.md`, `docs/b.md`.\n")
        text = replace_once(text, "**Files reviewed:** 2 of 2", "**Files reviewed:** 2 of 4")
        text = with_verdict(text, excluded=2)
        self.assertEqual(check_report(text), [])
        self.assertTrue(line_of(text, "Ready to merge").startswith("**Ready to merge:** Yes"))

    def test_unknown_tag_fails(self):
        text = replace_once(FIXTURE, "API not validated, not material:", "skipped, not material:")
        self.assertError(check_report(text), "Not verified item is malformed")

    def test_missing_weight_fails(self):
        text = replace_once(FIXTURE, "API not validated, not material:", "API not validated:")
        self.assertError(check_report(text), "Not verified item is malformed")

    def test_unrun_test_result_fails(self):
        text = set_line(FIXTURE, "Relevant tests", "**Relevant tests:** existing — `tests/orders.test.js` passes. "
                        "Execution: not run.")
        self.assertError(check_report(text), "claims a test result, but Execution is not run")
        text = set_line(FIXTURE, "Relevant tests", "**Relevant tests:** existing — all tests passed. Execution: not run.")
        self.assertError(check_report(text), "claims a test result, but Execution is not run")

    def test_failure_words_in_coverage_are_fine(self):
        text = set_line(FIXTURE, "Relevant tests", "**Relevant tests:** existing — `tests/orders.test.js` covers failed "
                        "payment attempts. Execution: not run.")
        self.assertEqual(check_report(text), [])

    def test_ran_tests_are_reported(self):
        text = set_line(FIXTURE, "Relevant tests", "**Relevant tests:** existing — `tests/orders.test.js` runs "
                        "`orderTotal` but not `listOrders`. Execution: ran `npm test -- tests/orders.test.js`; "
                        "4 passed, 0 failed.")
        self.assertEqual(check_report(text), [])
        text = set_line(FIXTURE, "Relevant tests", "**Relevant tests:** existing — `tests/orders.test.js` runs "
                        "`orderTotal` but not `listOrders`. Execution: partly ran `npm test -- tests/orders.test.js`; "
                        "4 passed, 0 failed; not run: the database tests, which need a running database.")
        self.assertEqual(check_report(text), [])

    def test_old_never_run_wording_fails(self):
        text = set_line(FIXTURE, "Relevant tests", "**Relevant tests:** existing — `tests/orders.test.js` runs "
                        "`orderTotal`. Not run by this review.")
        self.assertError(check_report(text), "**Relevant tests:** line does not match its form")

    def test_relevant_tests_not_verified_needs_audit_item(self):
        text = set_line(FIXTURE, "Relevant tests", "**Relevant tests:** not verified — `tests/orders.test.js` could not "
                        "be opened. Execution: not run.")
        self.assertError(check_report(text), "is not verified, but the Audit has no tests not verified item")
        with_tnv = with_items(text, API_ITEM, TNV_ITEM)
        self.assertEqual(check_report(with_tnv), [])
        self.assertError(check_report(with_items(FIXTURE, API_ITEM, TNV_ITEM)), "the Audit has a tests not verified item")

    def test_tests_not_verified_category_is_not_clean(self):
        text = set_line(FIXTURE, "Relevant tests", "**Relevant tests:** not verified — `tests/orders.test.js` could not "
                        "be opened. Execution: not run.")
        text = with_items(text, API_ITEM, TNV_ITEM)
        text = set_line(text, "Checked with no findings", "**Checked with no findings:** Tests/Coverage, Architecture, "
                        "Code & File Size.")
        self.assertError(check_report(text), "names Tests/Coverage, but the relevant tests were not verified")

    def test_raised_warning_candidate_is_with_fixes(self):
        text = as_pr(no_findings(FIXTURE))
        self.assertEqual(check_report(with_verdict(text, raised=1)), [])
        self.assertError(check_report(with_verdict(text)), "Ready to merge line is")

    def test_pr_audit_needs_already_raised_line(self):
        text = as_pr(no_findings(FIXTURE))
        self.assertError(check_report(replace_once(text, ALREADY + "\n", "")),
                         "line is missing in a pr review")
        text = replace_once(text, ALREADY, "**Already raised, not verified:** none.")
        self.assertEqual(check_report(with_verdict(text)), [])

    def test_already_raised_line_outside_pr_fails(self):
        text = replace_once(FIXTURE, CHECKED + "\n", CHECKED + "\n" + ALREADY + "\n")
        self.assertError(check_report(text), "line is only for a pr review")

    def test_raised_candidate_must_be_under_already_raised(self):
        text = replace_once(as_pr(no_findings(FIXTURE)), ALREADY, ALREADY.replace("orders.js:40", "orders.js:41"))
        self.assertError(check_report(text), "names src/orders.js:41, which is not under Already raised in the PR")

    def test_raised_category_is_not_clean(self):
        text = replace_once(as_pr(no_findings(FIXTURE)), CHECKED,
                            "**Checked with no findings:** Architecture, Code & File Size, Potential Bugs.")
        self.assertError(check_report(text), "which has a Warning candidate already raised")

    def test_raised_critical_stays_a_finding(self):
        self.assertEqual(check_report(as_pr(FIXTURE)), [])

    def test_audit_lists_every_path(self):
        self.assertEqual(check_report(with_verdict(wide(no_findings(FIXTURE), 25))), [])

    def test_audit_path_cap_fails(self):
        capped = ", ".join(f"`src/f{i:02d}.js`" for i in range(20)) + ", and 5 more"
        text = set_line(wide(no_findings(FIXTURE), 25), "Files reviewed", f"**Files reviewed:** 25 of 25 changed files: "
                        f"{capped}.")
        self.assertError(check_report(text), "**Files reviewed:** line is malformed")

    def test_files_reviewed_count(self):
        text = replace_once(FIXTURE, "**Files reviewed:** 2 of 2 changed files", "**Files reviewed:** 3 of 2 changed files")
        self.assertError(check_report(text), "Files reviewed counts more files than changed")
        self.assertError(check_report(wide(no_findings(FIXTURE), 24)), "Files reviewed lists 24 paths but counts 25")

    def test_context_count_must_match(self):
        text = replace_once(FIXTURE, "**Read for context:** 2 files:", "**Read for context:** 3 files:")
        self.assertError(check_report(text), "Read for context lists 2 paths but counts 3")

    def test_audit_is_last_section(self):
        text = FIXTURE + "\n## Action Items\n\n1. Bind the status parameter.\n"
        self.assertError(check_report(text), "## Audit must be the last section of the report")

    def test_clean_category_with_a_finding_fails(self):
        text = replace_once(FIXTURE, CHECKED, "**Checked with no findings:** Security, Architecture.")
        self.assertError(check_report(text), "Checked with no findings names Security, which has a finding")

    def test_triage_order(self):
        relevant, look = line_of(FIXTURE, "Relevant tests"), line_of(FIXTURE, "Look first")
        text = replace_once(FIXTURE, relevant + "\n" + look + "\n", look + "\n" + relevant + "\n")
        self.assertError(check_report(text), "triage lines are not consecutive")

    def test_look_first_names_reviewed_files(self):
        text = set_line(FIXTURE, "Look first", "**Look first:** `src/other.js` (it changed).")
        self.assertError(check_report(text), "Look first names src/other.js, which is not a reviewed file")

    def test_passed_report_keeps_triage_and_audit(self):
        text = no_findings(FIXTURE)
        text = drop_heading(text, "## Findings")
        text = drop_heading(text, "## Needs human verification")
        text = replace_once(text, "- The new handler validates its input with the route schema.\n",
                            "- The new handler validates its input with the route schema.\n\n"
                            "Code review passed — no issues found.\n")
        text = with_verdict(text)
        self.assertEqual(check_report(text), [])
        self.assertTrue(looks_like_report(text))

    def test_compact_audit_line(self):
        audit = parse_audit(FIXTURE)
        self.assertEqual(compact_audit_line(audit), COMPACT_FIXTURE)
        self.assertIsNotNone(COMPACT_AUDIT.match(COMPACT_FIXTURE))
        self.assertIn("; already raised, not verified: 1 Warning candidate; not verified: ",
                      compact_audit_line(parse_audit(as_pr(no_findings(FIXTURE)))))


class MatrixTests(Base):
    def test_rows(self):
        cases = [
            (dict(reviewed=0), "**Ready to merge:** No — not fully reviewed: no changed file was reviewed."),
            (dict(critical=2, warning=1), "**Ready to merge:** No — 2 Critical findings must be fixed before merging."),
            (dict(critical=1, material=[L]), "**Ready to merge:** No — 1 Critical finding must be fixed before merging. "
             "Not fully reviewed: see the Audit."),
            (dict(material=[L], warning=3), "**Ready to merge:** No — not fully reviewed (not read): "
             "`src/a.js` lines 10-90."),
            (dict(material=[W, C]), "**Ready to merge:** No — not fully reviewed (not read): `src/pay.js` (whole file). "
             "1 more material limit is in the Audit."),
            (dict(material=[W, C, A]), "**Ready to merge:** No — not fully reviewed (not read): `src/pay.js` "
             "(whole file). 2 more material limits are in the Audit."),
            (dict(material=[A], needs=1), "**Ready to merge:** No — not fully reviewed (API not validated): "
             "`pg` query options in `src/orders.js`."),
            (dict(warning=2, omitted_warning=1), "**Ready to merge:** With fixes — 2 Warning findings (1 omitted by "
             "configuration) should be fixed; none blocks the merge."),
            (dict(needs=1), "**Ready to merge:** With fixes — a person must check 1 finding under Needs human "
             "verification before merging."),
            (dict(raised=1), "**Ready to merge:** With fixes — 1 Warning candidate already raised in an open thread "
             "still needs verification before merging."),
            (dict(raised=2), "**Ready to merge:** With fixes — 2 Warning candidates already raised in open threads "
             "still need verification before merging."),
            (dict(), "**Ready to merge:** Yes — no Critical or Warning findings."),
            (dict(critical=1, material=[("`x.js` lines 1-2", "not read")], excluded=1),
             "**Ready to merge:** No — 1 Critical finding must be fixed before merging. Not fully reviewed: see the "
             "Audit. 1 changed file excluded by configuration was not reviewed."),
            (dict(excluded=2), "**Ready to merge:** Yes — no Critical or Warning findings. 2 changed files excluded by "
             "configuration were not reviewed."),
            (dict(critical=1, raised=1), "**Ready to merge:** No — 1 Critical finding must be fixed before merging."),
            (dict(needs=2, omitted_needs=1), "**Ready to merge:** With fixes — a person must check 2 findings (1 omitted "
             "by configuration) under Needs human verification before merging."),
            (dict(needs=1, omitted_needs=1), "**Ready to merge:** With fixes — a person must check 1 finding (1 omitted "
             "by configuration) under Needs human verification before merging."),
        ]
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                self.assertEqual(verdict_line(**kwargs), expected)


class EffortTests(Base):
    def test_levels(self):
        cases = {(40, 0): 1, (50, 0): 1, (51, 0): 2, (200, 0): 2, (201, 0): 3, (500, 0): 3, (501, 0): 4,
                 (1000, 0): 4, (1001, 0): 5, (40, 1): 2, (40, 2): 3, (40, 3): 3, (120, 1): 3, (760, 2): 5}
        for (changed_lines, risks), level in cases.items():
            with self.subTest(changed_lines=changed_lines, risks=risks):
                self.assertEqual(effort_level(changed_lines, risks), level)


class ParserTests(Base):
    def test_triage_and_audit_are_not_findings(self):
        head = FIXTURE[:FIXTURE.index("\n## Audit\n")]
        stripped = "\n".join(line for line in head.split("\n")
                            if not any(line.startswith(f"**{label}:**") for label in TRIAGE))
        self.assertEqual(parse_findings(FIXTURE), parse_findings(stripped))
        self.assertEqual(score_clean(FIXTURE), score_clean(stripped))
        self.assertEqual(score_bug(FIXTURE, ["SQL"], "Critical"), score_bug(stripped, ["SQL"], "Critical"))
        self.assertTrue(score_bug(FIXTURE, ["SQL"], "Critical")["detected"])

    def test_pr_audit_line_is_not_a_finding(self):
        pr = as_pr(FIXTURE)
        self.assertEqual(parse_findings(pr), parse_findings(replace_once(pr, ALREADY + "\n", "")))

    def test_publishing_fixture_parses_the_same(self):
        publishing = read("fixtures/publishing/report.md")
        combined = (publishing + "\n\n" + triage_block(FIXTURE) + "\n\n"
                    + FIXTURE[FIXTURE.index("## Audit"):])
        self.assertEqual(parse_findings(combined), parse_findings(publishing))

    def test_compact_report_parses_the_same(self):
        report = ("**Scope:** staged (git diff --cached)\n\n"
                  "- src/orders.js:12: Critical: the status is concatenated into SQL → bind it\n\n"
                  "**Verification:** 1 Critical/Warning candidates checked, 0 refuted.\n")
        full = (report + triage_block(FIXTURE) + "\n"
                "**Audit:** 1 of 1 changed file reviewed; 0 files read for context; no findings in no category; "
                "not verified: nothing.\n")
        self.assertEqual(parse_findings(full), parse_findings(report))
        self.assertEqual(len([f for f in parse_findings(full) if f["compact"]]), 1)


class SummaryTests(Base):
    def test_summary_carries_triage(self):
        compact = compact_audit_line(parse_audit(FIXTURE))
        body = ("<!-- code-review-skill:summary -->\n## Code review\n\n"
                "**Verification:** 3 Critical/Warning candidates checked, 0 refuted.\n\n"
                + triage_block(FIXTURE) + "\n" + compact)
        self.assertEqual(check_summary_triage(body, FIXTURE, compact), [])

        ready = line_of(FIXTURE, "Ready to merge")
        self.assertError(check_summary_triage(body.replace(ready + "\n", ""), FIXTURE, compact),
                         "summary misses the triage line")
        self.assertError(check_summary_triage(body.replace(compact, ""), FIXTURE, compact),
                         "summary misses the audit line")
        self.assertTrue(inline_has_triage(body))
        self.assertFalse(inline_has_triage("**Issue:** x"))


class ExampleOutputTests(Base):
    def test_full_report(self):
        full = example_full()
        self.assertEqual(check_report(full), [])
        self.assertEqual(line_of(full, "Ready to merge"), CRITICAL_VERDICT)
        self.assertEqual(parse_audit(full)["raised"], [("src/routes/auth.routes.ts:8", "Security")])

    def test_limit_weights_follow_their_dependencies(self):
        full = example_full()
        items = parse_audit(full)["items"]
        self.assertEqual([what for what, _tag, weight, _detail in items if weight == "material"],
                         ["gateway configuration"])
        gateway = [detail for what, _tag, _weight, detail in items if what == "gateway configuration"]
        self.assertIn("serializes requests per user", gateway[0])
        self.assertNotIn("jwt.sign", "\n".join(audit_lines(full)))

    def test_action_items_are_outside_the_report(self):
        self.assertLess(EXAMPLE.index("## Audit"), EXAMPLE.index(REPORT_END))
        self.assertLess(EXAMPLE.index(REPORT_END), EXAMPLE.index("## Action Items"))

    def test_compact_mode(self):
        full = example_full()
        compact = EXAMPLE[EXAMPLE.index("## Compact Mode"):EXAMPLE.index("## Coverage Limits")]
        lines = compact.split("\n")
        self.assertEqual(triage_lines(compact), triage_lines(full))
        self.assertEqual(line_of(compact, "Ready to merge"), CRITICAL_VERDICT)
        self.assertEqual([line for line in lines if line.startswith("**Audit:** ")],
                         [compact_audit_line(parse_audit(full))])
        self.assertNotIn("## Audit", lines)
        self.assertGreater(find_line(lines, "**Review effort:** "), find_line(lines, "**Verification:**"))

    def test_coverage_limits(self):
        section = EXAMPLE[EXAMPLE.index("## Coverage Limits"):EXAMPLE.index("## Repository Configuration")]
        blocks = re.findall(r"```markdown\n(.*?)```", section, re.S)
        combined = "\n\n".join(blocks)
        self.assertEqual(check_report(combined), [])
        self.assertTrue(line_of(combined, "Ready to merge").startswith(
            "**Ready to merge:** No — not fully reviewed (not read): `src/legacy/report.ts` lines 1201-2310."))
        items = parse_audit(combined)["items"]
        self.assertIn("material", [weight for _what, _tag, weight, _detail in items])
        self.assertIn("not material", [weight for _what, _tag, weight, _detail in items])
        self.assertIn("tests not verified", [tag for _what, tag, _weight, _detail in items])
        tests = [(weight, detail) for _what, tag, weight, detail in items if tag == "tests not verified"]
        self.assertEqual(tests[0][0], "not material")
        self.assertIn("judged from the code", tests[0][1])

    def test_dry_run_summary(self):
        full = example_full()
        compact = compact_audit_line(parse_audit(full))
        dry = EXAMPLE[EXAMPLE.index("## Dry run — nothing was published"):]
        payloads = [json.loads(block) for block in re.findall(r"```json\n(.*?)```", dry, re.S)]
        summaries = [p["body"] for p in payloads if p["body"].startswith("<!-- code-review-skill:summary -->")]
        self.assertEqual(len(summaries), 1)
        self.assertIn(CRITICAL_VERDICT, summaries[0].split("\n"))
        self.assertEqual(check_summary_triage(summaries[0], full, compact), [])
        for payload in payloads:
            for comment in payload.get("comments", []):
                self.assertIs(inline_has_triage(comment["body"]), False)


class ToolTests(Base):
    def test_eval_runner_keeps_mcp_off(self):
        self.assertIn("--strict-mcp-config", run.DEFAULT_AGENT_CMD)
        self.assertIn("--safe-mode", run.DEFAULT_AGENT_CMD)


if __name__ == "__main__":
    unittest.main()
