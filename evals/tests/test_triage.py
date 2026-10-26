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
TAGS = ("not read", "binary", "context not read", "API not validated", "tests not verified", "dimension not reviewed")
WEIGHTS = ("material", "not material")
SIZES = ("up to 50", "51 to 200", "201 to 500", "501 to 1000", "more than 1000")
RISK_AREAS = ("authentication", "authorization", "payments", "personal data", "database schema or migrations",
              "concurrency", "public API contracts")
EFFORT_CLAIM = r"^\*\*Review effort:\*\* ([1-5])/5 — (?:(at least )?(\d+)|(" + "|".join(SIZES) + r")) changed lines?"
EFFORT_CLAIM_RE = re.compile(EFFORT_CLAIM)
EFFORT_LEVEL_RE = re.compile(r"\b[1-5]/5\b")
EFFORT_SIZE_RE = re.compile("|".join(re.escape(size) for size in SIZES))
EFFORT_TABLE_RE = re.compile(r"^\| `(" + "|".join(SIZES) + r")` \| ([1-5])/5 \| ([1-5])/5 \| ([1-5])/5 \|$", re.M)
LINE_RES = {
    "Review effort": re.compile(EFFORT_CLAIM + r" in (\d+) files?( \(the total could not be measured: [^()]+\))?; "
                                r"(\S.*)\.$"),
    "Relevant tests": re.compile(
        r"^\*\*Relevant tests:\*\* (changed|existing|missing|not applicable|not verified) — (\S.*?)\. "
        r"Execution: (not run|ran `[^`]+`(?:, `[^`]+`)*; \S.*|partly ran `[^`]+`(?:, `[^`]+`)*; \S.*; not run: \S.*)\.$"),
    "Look first": re.compile(r"^\*\*Look first:\*\* (?:no reviewed file|`[^`]+` \([^)]+\)(?:, `[^`]+` \([^)]+\)){0,2})\.$"),
    "Ready to merge": re.compile(r"^\*\*Ready to merge:\*\* (?:Yes|No|With fixes) — \S.*\.$"),
}
RESULT_RE = re.compile(r"(?i)(?:\b(?:tests?|suites?|specs?)\b|`[^`]*(?:test|spec)[^`]*`)\s+(?:all\s+)?(?:pass(?:es|ed)?|fail(?:s|ed)?)\b")
ITEM_RE = re.compile(r"^- (.+?) — (not read|binary|context not read|API not validated|tests not verified|dimension not reviewed), (material|not material): (\S.*)$")
COMPACT_AUDIT = re.compile(r"^\*\*Audit:\*\* (\d+) of (\d+) changed files? reviewed; (\d+) files? read for context; no findings in (.+?); (?:already raised, not verified: (\d+) Warning candidates?; )?not verified: (.+)\.$")
FILES_RE = re.compile(r"^\*\*Files reviewed:\*\* (\d+) of (\d+) changed files?(?:: (.+))?\.$")
CONTEXT_RE = re.compile(r"^\*\*Read for context:\*\* (?:none|(\d+) files?: (.+)|(`.+))\.$")
CLEAN_RE = re.compile(r"^\*\*Checked with no findings:\*\* (.+)\.$")
RAISED_RE = re.compile(r"^\*\*Already raised, not verified:\*\* (.+)\.$")
RAISED_ENTRY_RE = re.compile(r"`([^`]+)` \(([^)]+)\)")
EXCLUDED_RE = re.compile(r"^\*\*Excluded by configuration:\*\* (\d+) changed files?\b")
DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
RAISED_HEADING = "## Already raised in the PR (not repeated)"

FINDING_BLOCKS = ("### Security — Critical", "### Potential Bugs — Warning", "### Performance — Warning")
API_ITEM = ("- `pg` query options in `src/orders.js` — API not validated, not material: no documentation tool was "
            "available; no changed behavior depends on these options.")
API_MATERIAL = ("- `pg` query options in `src/orders.js` — API not validated, material: no documentation tool was "
                "available, and the order of the changed query's rows depends on these options.")
TNV_ITEM = "- relevant tests — tests not verified, not material: `tests/orders.test.js` could not be opened."
CHECKED = "**Checked with no findings:** Architecture, Code & File Size."
ALREADY = "**Already raised, not verified:** `src/orders.js:40` (Potential Bugs)."
HEADLINE_PASSED = "Code review passed — no issues found."
HEADLINE_INCOMPLETE = "Review incomplete or pending — no confirmed findings in the code inspected."
NO_FINDINGS_SHOWN = ("**No findings shown:** the configuration omitted every finding; see the Omitted by "
                     "configuration line.")
ROUTES_LIMIT = ("`src/routes.js` lines 40-90", "not read")
ROUTES_ITEM = "- `src/routes.js` lines 40-90 — not read, material: the diff output was cut off."
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
SKILL = read(os.path.join("..", "..", "SKILL.md"))
DIMENSIONS = read(os.path.join("..", "..", "references", "dimensions.md"))
DIMENSION_ITEM_RE = re.compile(r"^(bugs|security|repository rules) dimension$")
REPORT_END = "The report ends with the Audit above."
CRITICAL_VERDICT = ("**Ready to merge:** No — 2 Critical findings must be fixed before merging. "
                    "Not fully reviewed: see the Audit.")


def example_full():
    return EXAMPLE[EXAMPLE.index("## Code Review Report"):EXAMPLE.index(REPORT_END)]


def plural(n, word):
    return f"{n} {word}" + ("s" if n != 1 else "")


def dimension_owners(text):
    """{owner: categories} from the Dimensions table of references/dimensions.md; the repository rules row owns none."""
    owners, in_table = {}, False
    for line in text.split("\n"):
        if line == "## Dimensions":
            in_table = True
        elif line.startswith("## "):
            in_table = False
        if not in_table or not line.startswith("| ") or line.startswith("| Owner ") or line.startswith("| ---"):
            continue
        owner, _checklist, cats = [c.strip() for c in line.strip().strip("|").split("|")]
        owners[owner] = () if cats.startswith("none of its own") else tuple(cats.split(", "))
    return owners


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


def size_of(changed_lines):
    """The size band of SIZES that a measured total falls in."""
    return SIZES[effort_level(changed_lines, 0) - 1]


def effort_table(text):
    """The level table of SKILL.md Step 3: {size: (no risk area, 1 risk area, 2 or more risk areas)}, in its order."""
    return {m.group(1): (int(m.group(2)), int(m.group(3)), int(m.group(4))) for m in EFFORT_TABLE_RE.finditer(text)}


def risk_count(text):
    """The number of RISK_AREAS the text names; 0 for the whole sentinel `no risk area`; None for other wording."""
    named = sum(area in text for area in RISK_AREAS)
    if named:
        return named
    return 0 if " ".join(text.lower().split()) == "no risk area" else None


def diff_line_count(diff, excluded=()):
    """Measured stats of a unified diff: (added plus removed lines, changed files) without the `excluded` paths.
    Only lines after a file's first @@ line count, so its --- and +++ headers never do; a binary file counts as a
    changed file with no lines."""
    lines = files = 0
    path, in_hunk = None, False
    for line in diff.split("\n"):
        header = DIFF_HEADER_RE.match(line)
        if header:
            path, in_hunk = header.group(2), False
            files += path not in excluded
        elif path is not None and path not in excluded:
            if line.startswith("@@"):
                in_hunk = True
            elif in_hunk and line[:1] in ("+", "-"):
                lines += 1
    return lines, files


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
    context = parse_paths(context_match.group(2) or context_match.group(3), "**Read for context:** line is malformed")
    stated = int(context_match.group(1)) if context_match.group(1) else None

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
        "context_count": len(context) if stated is None else stated,
        "context_stated": stated,
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


def _check_files(audit, excluded, excluded_paths=()):
    reviewed, changed, paths = audit["reviewed"], audit["changed"], audit["paths"]
    context = audit["context"]
    errors = []
    if reviewed > changed:
        errors.append("Files reviewed counts more files than changed")
    if len(paths) != reviewed:
        errors.append(f"Files reviewed lists {len(paths)} paths but counts {reviewed}")
    if paths != sorted(set(paths)):
        errors.append("Files reviewed paths must be unique and in alphabetical order")
    unread = [item for item in audit["items"] if item[1] == "not read" and item[0].endswith(" (whole file)")]
    binary = [item for item in audit["items"] if item[1] == "binary"]
    for what, tag, _weight, _detail in unread + binary:
        m = re.search(r"`([^`]+)`", what)
        if m and m.group(1) in paths:
            errors.append(f"Files reviewed lists `{m.group(1)}`, which the Audit also lists as {tag}")
    changed_paths = set(paths) | set(excluded_paths)
    for what, _tag, _weight, _detail in unread + binary:
        changed_paths.update(re.findall(r"`([^`]+)`", what))
    errors += _check_context(context, audit["context_stated"], changed_paths)
    u, b = len(unread), len(binary)
    if reviewed + excluded + b + u != changed:
        errors.append(f"Files reviewed: {reviewed} reviewed, {excluded} excluded, {b} binary and {u} not read "
                      f"do not add up to {changed} changed files")
    return errors


def _check_context(context, stated, changed_paths):
    """The Read for context rules; the count is compared only when the line states one."""
    errors = []
    if stated is not None and len(context) != stated:
        errors.append(f"Read for context lists {len(context)} paths but counts {stated}")
    if context != sorted(set(context)):
        errors.append("Read for context paths must be unique and in alphabetical order")
    for path in context:
        if path in changed_paths:
            errors.append(f"Read for context names `{path}`, which is a changed file")
        if path == "skill:SKILL.md":
            errors.append("Read for context names `skill:SKILL.md`, the instructions of the review")
    return errors


def _check_audit_lines(text):
    """The checks of the well-formed Files reviewed and Read for context lines of an Audit that parse_audit rejected."""
    try:
        body = audit_lines(text)
    except ValueError:
        return []
    errors, reviewed = [], set()
    for line in body:
        files = FILES_RE.match(line)
        context_match = CONTEXT_RE.match(line)
        if files:
            try:
                paths = parse_paths(files.group(3), "")
            except ValueError:
                continue
            if len(paths) != int(files.group(1)):
                errors.append(f"Files reviewed lists {len(paths)} paths but counts {files.group(1)}")
            reviewed.update(paths)
        elif context_match:
            try:
                listed = parse_paths(context_match.group(2) or context_match.group(3), "")
            except ValueError:
                continue
            stated = int(context_match.group(1)) if context_match.group(1) else None
            errors += _check_context(listed, stated, reviewed)
    return errors


def _check_clean(audit, finding_categories, tests_not_verified, unreviewed=frozenset()):
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
        if cat in unreviewed:
            errors.append(f"Checked with no findings names {cat}, but its dimension was not reviewed")
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


def _check_effort(line, changed_lines=None):
    """The Review effort rules. The count or size is checked even when the rest of the line is malformed; the level
    is checked against the size and the named risk areas, and skipped when the line names none in those words."""
    errors = []
    levels = list(dict.fromkeys(EFFORT_LEVEL_RE.findall(line)))
    sizes = list(dict.fromkeys(EFFORT_SIZE_RE.findall(line)))
    if len(levels) > 1:
        errors.append(f"Review effort states different levels: {', '.join(levels)}")
    if len(sizes) > 1:
        errors.append(f"Review effort names different sizes: {', '.join(sizes)}")
    claim = EFFORT_CLAIM_RE.match(line)
    if not claim:
        return errors
    full = LINE_RES["Review effort"].match(line)
    level, at_least, size = int(claim.group(1)), claim.group(2), claim.group(4)
    counted = int(claim.group(3)) if claim.group(3) else None
    why = full.group(6) if full else None
    if full and at_least and not why:
        errors.append(f"Review effort counts at least {counted} changed lines without saying why the total "
                      "could not be measured")
    if why and size:
        errors.append(f"Review effort gives {size} changed lines, but says the total could not be measured")
    elif why and not at_least:
        errors.append(f"Review effort counts exactly {counted} changed lines, but says the total could not be measured")
    if at_least and level != 5:
        errors.append(f"Review effort counts at least {counted} changed lines, so its level must be 5/5")
    if at_least and changed_lines is not None:
        errors.append(f"Review effort counts at least {counted} changed lines, but the diff has {changed_lines}, "
                      "a complete measured total")
    if counted is not None and not at_least and changed_lines is not None and counted != changed_lines:
        errors.append(f"Review effort counts {counted} changed lines, but the diff has {changed_lines}")
    if size and changed_lines is not None and size != size_of(changed_lines):
        errors.append(f"Review effort gives {size} changed lines, but the diff has {changed_lines}")
    risks = risk_count(full.group(7)) if full and not at_least else None
    if risks is not None:
        base = SIZES.index(size) + 1 if size else effort_level(counted, 0)
        want = min(base + min(risks, 2), 5)
        if level != want:
            errors.append(f"Review effort is {level}/5, but {size or counted} changed lines with "
                          f"{plural(risks, 'risk area')} give {want}/5")
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
    if effort and int(effort.group(5)) != audit["changed"] - excluded:
        errors.append(f"Review effort counts {effort.group(5)} files, but {audit['changed'] - excluded} "
                      "changed files are not excluded by configuration")

    relevant = LINE_RES["Relevant tests"].match(triage["Relevant tests"])
    if relevant:
        status = relevant.group(1)
        if status == "not verified" and not tests_not_verified:
            errors.append("**Relevant tests:** is not verified, but the Audit has no tests not verified item")
        if tests_not_verified and status != "not verified":
            errors.append(f"the Audit has a tests not verified item, but **Relevant tests:** is {status}")
    return errors


def check_report(text, *, omitted_warning=0, omitted_needs=0, changed_lines=None):
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

    excluded, excluded_paths = 0, []
    for line in lines:
        m = EXCLUDED_RE.match(line)
        if m:
            excluded, excluded_paths = int(m.group(1)), re.findall(r"`([^`]+)`", line)
            break

    audit_at = lines.index("## Audit") if "## Audit" in lines else None
    if audit_at is not None:
        if at["Ready to merge"] is not None and audit_at < at["Ready to merge"]:
            errors.append("## Audit must come after the triage lines")
        if any(line.startswith("#") for line in lines[audit_at + 1:]):
            errors.append("## Audit must be the last section of the report")

    errors += headline_errors(text, omitted_warning + omitted_needs)
    errors += _check_effort(triage["Review effort"], changed_lines)
    try:
        audit = parse_audit(text)
    except ValueError as error:
        return errors + [str(error)] + _check_audit_lines(text)

    scope = find_line(lines, "**Scope:**")
    is_pr = scope is not None and lines[scope].startswith("**Scope:** pr ")
    items = audit["items"]
    tests_not_verified = any(tag == "tests not verified" for _what, tag, _weight, _detail in items)
    unreviewed, owners = set(), dimension_owners(DIMENSIONS)
    for what, tag, _weight, _detail in items:
        if tag != "dimension not reviewed":
            continue
        m = DIMENSION_ITEM_RE.match(what)
        if m is None:
            errors.append(f"dimension not reviewed names {what!r}; it must be the bugs, security or repository "
                          "rules dimension")
        else:
            unreviewed.update(owners[m.group(1)])

    errors += _check_files(audit, excluded, excluded_paths)
    errors += _check_clean(audit, finding_categories, tests_not_verified, unreviewed)
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


def headline_errors(text, omitted=0):
    """Errors for the headline of a report, in full or compact form: the passed sentence only for Ready to merge Yes
    and no listed finding; the incomplete sentence never beside Yes; a headline never beside listed findings; and
    when a filter omitted findings and none is listed, the No findings shown line in place of the headline."""
    lines = text.split("\n")
    at = find_line(lines, "**Ready to merge:** ")
    ready = lines[at] if at is not None else ""
    findings = [f for f in parse_findings(text) if not (f["pre_existing"] or f["already_raised"])]
    listed = [f for f in findings if not f["needs_verification"]]
    found = [h for h in map(headline_of, lines) if h is not None]
    notice = [h for h in found if h.lstrip("*").startswith("No findings shown:")]
    errors = []
    if listed and found:
        errors.append(f"headline {found[0]!r} contradicts the findings listed in the report")
    elif omitted and not findings and not notice:
        errors.append("findings were omitted by configuration: the headline must be the No findings shown line")
    if len(found) > 1:
        errors.append("the report has more than one headline")
    elif found and found[0] == HEADLINE_PASSED and ready and not ready.startswith("**Ready to merge:** Yes — "):
        errors.append(f"headline {HEADLINE_PASSED!r} needs Ready to merge: Yes")
    elif found and found[0] == HEADLINE_INCOMPLETE and ready.startswith("**Ready to merge:** Yes — "):
        errors.append("the incomplete headline contradicts Ready to merge: Yes")
    return errors


def missing_headline_errors(text):
    """The error when no main finding is listed under ## Findings and the report carries no headline. Kept apart from
    check_report: reports without findings are built without a headline on purpose in earlier tests."""
    findings = [f for f in parse_findings(text) if not (f["pre_existing"] or f["already_raised"] or f["needs_verification"])]
    if findings or headlines(text):
        return []
    return ["no finding is listed under ## Findings, so the report needs its headline"]


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


def clean_report(text):
    """The fixture without any finding block or finding heading."""
    text = drop_heading(no_findings(text), "## Findings")
    return drop_heading(text, "## Needs human verification")


def unreviewed(text):
    """The fixture after no changed file could be read."""
    text = no_findings(text)
    text = set_line(text, "Files reviewed", "**Files reviewed:** 0 of 2 changed files.")
    text = set_line(text, "Checked with no findings", "**Checked with no findings:** none.")
    text = set_line(text, "Look first", "**Look first:** no reviewed file.")
    text = set_line(text, "Relevant tests", "**Relevant tests:** not verified — no changed file could be read. "
                    "Execution: not run.")
    return with_items(
        text,
        "- `src/orders.js` (whole file) — not read, material: it could not be opened.",
        "- `src/routes.js` (whole file) — not read, material: it could not be opened.",
        "- relevant tests — tests not verified, not material: no changed file could be read.")


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
    text = set_line(text, "Review effort", "**Review effort:** 4/5 — 300 changed lines in 25 files; payments.")
    return set_line(text, "Look first", "**Look first:** `src/f00.js` (the largest change).")


def triage_block(text):
    return "\n".join(line for line in triage_lines(text) if line is not None)


def headline_of(line):
    """The headline of a line: a passed or incomplete sentence without its bold markers, or the whole No findings shown line."""
    norm = line.strip().strip("*").strip()
    if norm in (HEADLINE_PASSED, HEADLINE_INCOMPLETE):
        return norm
    if line.strip().lstrip("*").startswith("No findings shown:"):
        return line.strip()
    return None


def headlines(text):
    return [h for h in map(headline_of, text.split("\n")) if h is not None]


def compact_form(text):
    """The report in compact mode: the same lines, with one **Audit:** line in place of ## Audit."""
    audit = compact_audit_line(parse_audit(text))
    return drop_block(text, "## Audit").rstrip("\n") + "\n" + audit + "\n"


def after_first_bullet(text, line):
    return replace_once(text, "- The new handler validates its input with the route schema.\n",
                        "- The new handler validates its input with the route schema.\n\n" + line + "\n")


def summary_of(text, headline):
    """A published summary as publishing.md writes it: the headline in place of the list, then the triage lines."""
    return ("<!-- code-review-skill:summary -->\n## Code review\n\n## Findings\n\n" + headline + "\n\n"
            + triage_block(text) + "\n" + compact_audit_line(parse_audit(text)) + "\n")


def check_summary_headline(body, report):
    """Errors when a published summary's headline differs from the report's."""
    want, got = headlines(report), headlines(body)
    return [] if got == want else [f"summary headline is {got!r}, report has {want!r}"]


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
        text = after_first_bullet(with_verdict(no_findings(FIXTURE), warning=1, omitted_warning=1), NO_FINDINGS_SHOWN)
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
        text = unreviewed(FIXTURE)
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


class HeadlineTests(Base):
    """The headline of a report with no listed finding follows Ready to merge, in full, compact and summary forms."""
    def cases(self):
        clean = clean_report(FIXTURE)
        return {
            "material-unread": (with_verdict(with_items(clean, ROUTES_ITEM), material=[ROUTES_LIMIT]),
                                HEADLINE_INCOMPLETE, [HEADLINE_PASSED], 0),
            "zero-reviewed": (with_verdict(unreviewed(clean), reviewed=0), HEADLINE_INCOMPLETE, [HEADLINE_PASSED], 0),
            "needs-only": (with_verdict(drop_block(drop_block(FIXTURE, FINDING_BLOCKS[0]), FINDING_BLOCKS[1]), needs=1),
                           HEADLINE_INCOMPLETE, [HEADLINE_PASSED], 0),
            "already-raised-only": (with_verdict(as_pr(clean), raised=1), HEADLINE_INCOMPLETE, [HEADLINE_PASSED], 0),
            "clean": (with_verdict(clean), HEADLINE_PASSED, [HEADLINE_INCOMPLETE], 0),
            "filtered-main-warning": (with_verdict(no_findings(FIXTURE), warning=1, omitted_warning=1),
                                      NO_FINDINGS_SHOWN, [HEADLINE_PASSED, HEADLINE_INCOMPLETE], 1),
        }

    def test_each_case_carries_its_headline_in_every_form(self):
        for name, (base, want, _wrong, omitted) in self.cases().items():
            text = after_first_bullet(base, want)
            with self.subTest(case=name, form="full"):
                self.assertEqual(check_report(text, omitted_warning=omitted), [])
                self.assertEqual(headlines(text), [want])
            with self.subTest(case=name, form="compact"):
                compact = compact_form(text)
                self.assertEqual(headline_errors(compact, omitted), [])
                self.assertEqual(headlines(compact), [want])
            with self.subTest(case=name, form="summary"):
                self.assertEqual(check_summary_headline(summary_of(text, want), text), [])

    def test_a_wrong_headline_is_rejected_in_every_form(self):
        for name, (base, want, wrong, omitted) in self.cases().items():
            right = after_first_bullet(base, want)
            for headline in wrong:
                text = after_first_bullet(base, headline)
                with self.subTest(case=name, form="full", headline=headline):
                    self.assertTrue(check_report(text, omitted_warning=omitted))
                with self.subTest(case=name, form="compact", headline=headline):
                    self.assertTrue(headline_errors(compact_form(text), omitted))
                with self.subTest(case=name, form="summary", headline=headline):
                    self.assertTrue(check_summary_headline(summary_of(text, headline), right))

    def test_headline_beside_listed_findings_is_rejected(self):
        self.assertError(headline_errors(after_first_bullet(FIXTURE, HEADLINE_PASSED)), "contradicts the findings")
        self.assertError(headline_errors(after_first_bullet(FIXTURE, HEADLINE_INCOMPLETE)), "contradicts the findings")

    def test_two_headlines_are_rejected(self):
        text = after_first_bullet(with_verdict(clean_report(FIXTURE)), HEADLINE_PASSED)
        self.assertError(headline_errors(after_first_bullet(text, HEADLINE_PASSED)), "more than one headline")


SAMPLE_DIFF = "\n".join([
    "diff --git a/src/a.sql b/src/a.sql",
    "index 1111111..2222222 100644",
    "--- a/src/a.sql",
    "+++ b/src/a.sql",
    "@@ -1,2 +1,3 @@",
    " SELECT 1;",
    "--- old comment",
    "+-- new comment",
    "+++ counter",
    "diff --git a/assets/logo.png b/assets/logo.png",
    "index 3333333..4444444 100644",
    "Binary files a/assets/logo.png and b/assets/logo.png differ",
    "diff --git a/src/generated/client.ts b/src/generated/client.ts",
    "new file mode 100644",
    "--- /dev/null",
    "+++ b/src/generated/client.ts",
    "@@ -0,0 +1,2 @@",
    "+export const a = 1;",
    "+export const b = 2;",
    "",
])
CONTEXT_LINE = "**Read for context:** 2 files: `package.json`, `tests/orders.test.js`."
EXCLUDED_SCOPE = ("**Scope:** staged (git diff --cached)\n**Excluded by configuration:** 2 changed files match "
                  "ignore_paths and were not reviewed: `docs/a.md`, `docs/b.md`.\n")
UNMEASURED = " (the total could not be measured: the diff output was cut off and no source counts the whole diff)"


class ConsistencyProbeTests(Base):
    """Synthetic probes for four contradiction shapes (headline, context, effort count), each with its consistent counterpart."""

    def test_s1_headline_above_a_listed_warning_is_rejected(self):
        text = with_verdict(drop_block(FIXTURE, FINDING_BLOCKS[0]), warning=1)
        self.assertEqual(check_report(text), [])
        bad = after_first_bullet(text, HEADLINE_INCOMPLETE + "\n\nThat headline is wrong for this report.")
        self.assertError(check_report(bad), "contradicts the findings listed in the report")
        self.assertError(headline_errors(compact_form(bad)), "contradicts the findings listed in the report")

    def test_incomplete_headline_without_main_findings_stays_valid(self):
        text = drop_block(drop_block(FIXTURE, FINDING_BLOCKS[0]), FINDING_BLOCKS[1])
        text = after_first_bullet(with_verdict(drop_heading(text, "## Findings"), needs=1), HEADLINE_INCOMPLETE)
        self.assertEqual(check_report(text), [])

    def test_s2_context_count_must_match_its_paths(self):
        bad = replace_once(FIXTURE, CONTEXT_LINE, CONTEXT_LINE.replace("2 files:", "3 files:"))
        self.assertError(check_report(bad), "Read for context lists 2 paths but counts 3")

    def test_s2_changed_file_is_never_context(self):
        bad = replace_once(FIXTURE, CONTEXT_LINE, "**Read for context:** 3 files: `package.json`, `src/orders.js`, "
                           "`tests/orders.test.js`.")
        self.assertError(check_report(bad), "Read for context names `src/orders.js`, which is a changed file")
        text = replace_once(FIXTURE, "**Scope:** staged (git diff --cached)\n", EXCLUDED_SCOPE)
        text = with_verdict(replace_once(text, "**Files reviewed:** 2 of 2", "**Files reviewed:** 2 of 4"),
                            critical=1, excluded=2)
        self.assertEqual(check_report(text), [])
        bad = replace_once(text, CONTEXT_LINE, "**Read for context:** 3 files: `docs/a.md`, `package.json`, "
                           "`tests/orders.test.js`.")
        self.assertError(check_report(bad), "Read for context names `docs/a.md`, which is a changed file")

    def test_same_relative_path_in_repo_and_skill_is_two_files(self):
        text = replace_once(FIXTURE, CONTEXT_LINE, "**Read for context:** 4 files: `package.json`, "
                            "`references/configuration.md`, `skill:references/configuration.md`, `tests/orders.test.js`.")
        self.assertEqual(check_report(text), [])
        dup = replace_once(FIXTURE, CONTEXT_LINE, "**Read for context:** 2 files: `skill:stacks/node.md`, "
                           "`skill:stacks/node.md`.")
        self.assertError(check_report(dup), "Read for context paths must be unique and in alphabetical order")

    def test_context_identities(self):
        text = replace_once(FIXTURE, CONTEXT_LINE, "**Read for context:** 4 files: `/home/dev/.config/git/attributes`, "
                            "`SKILL.md`, `package.json`, `tests/orders.test.js`.")
        self.assertEqual(check_report(text), [])
        active = replace_once(FIXTURE, CONTEXT_LINE, "**Read for context:** 3 files: `package.json`, `skill:SKILL.md`, "
                              "`tests/orders.test.js`.")
        self.assertError(check_report(active), "Read for context names `skill:SKILL.md`, the instructions of the review")
        changed = replace_once(FIXTURE, "**Files reviewed:** 2 of 2 changed files: `src/orders.js`",
                               "**Files reviewed:** 3 of 3 changed files: `SKILL.md`, `src/orders.js`")
        changed = set_line(changed, "Review effort", "**Review effort:** 3/5 — 120 changed lines in 3 files; payments.")
        own = replace_once(changed, CONTEXT_LINE, "**Read for context:** 3 files: `package.json`, "
                           "`skill:stacks/node.md`, `tests/orders.test.js`.")
        self.assertEqual(check_report(own), [])
        bad = replace_once(changed, CONTEXT_LINE, "**Read for context:** 3 files: `SKILL.md`, `package.json`, "
                           "`tests/orders.test.js`.")
        self.assertError(check_report(bad), "Read for context names `SKILL.md`, which is a changed file")

    def test_context_line_forms(self):
        self.assertEqual(check_report(replace_once(FIXTURE, CONTEXT_LINE, "**Read for context:** none.")), [])
        for bad in ("**Read for context:** 0 files: none.",
                    CONTEXT_LINE[:-1] + ". I also read the skill files."):
            with self.subTest(line=bad):
                self.assertError(check_report(replace_once(FIXTURE, CONTEXT_LINE, bad)),
                                 "**Read for context:** line is malformed")

    def test_s3_material_limit_with_critical_needs_the_suffix(self):
        text = with_items(FIXTURE, MATERIAL_CONTEXT)
        self.assertError(check_report(with_verdict(text, critical=1)), "Ready to merge line is")
        self.assertEqual(check_report(with_verdict(text, critical=1, material=[CTX])), [])

    def test_s4_effort_count_must_match_the_diff(self):
        self.assertEqual(check_report(FIXTURE), [])
        self.assertEqual(check_report(FIXTURE, changed_lines=120), [])
        exact = set_line(FIXTURE, "Review effort", "**Review effort:** 5/5 — 711 changed lines in 2 files; payments.")
        self.assertEqual(check_report(exact, changed_lines=711), [])
        bad = set_line(FIXTURE, "Review effort", "**Review effort:** 5/5 — 668 changed lines in 2 files; payments.")
        self.assertError(check_report(bad, changed_lines=711), "Review effort counts 668 changed lines, but the diff has 711")

    def test_lower_bound_only_when_the_total_is_not_measured(self):
        bound = set_line(FIXTURE, "Review effort", "**Review effort:** 5/5 — at least 600 changed lines in 2 files"
                         + UNMEASURED + "; payments.")
        self.assertEqual(check_report(bound), [])
        self.assertError(check_report(bound, changed_lines=711),
                         "Review effort counts at least 600 changed lines, but the diff has 711, a complete measured total")
        self.assertError(check_report(bound.replace("5/5 — at least", "3/5 — at least")),
                         "Review effort counts at least 600 changed lines, so its level must be 5/5")
        self.assertError(check_report(bound.replace(UNMEASURED, "")),
                         "Review effort counts at least 600 changed lines without saying why the total could not be measured")
        self.assertError(check_report(bound.replace("at least 600", "600")),
                         "Review effort counts exactly 600 changed lines, but says the total could not be measured")

    def test_diff_line_count(self):
        self.assertEqual(diff_line_count(SAMPLE_DIFF), (5, 3))
        self.assertEqual(diff_line_count(SAMPLE_DIFF, excluded=("src/generated/client.ts",)), (3, 2))
        self.assertEqual(diff_line_count(""), (0, 0))


SIZED = "**Review effort:** 3/5 — 51 to 200 changed lines in 2 files; payments."
BARE_CONTEXT = "**Read for context:** `package.json`, `tests/orders.test.js`."


class RepairProbeTests(Base):
    """Probes shaped like the failures of the 82d7dba candidate: an empty Findings section, size bands, a context
    line without a count, and semantic checks that still run when another line of the report is malformed."""

    def clean_yes(self, line):
        """The fixture with no finding and Ready to merge Yes; `line`, when given, is the only line under ## Findings."""
        text = with_verdict(drop_heading(no_findings(FIXTURE), "## Needs human verification"))
        return replace_once(text, "## Findings\n", "## Findings\n\n" + line + "\n") if line else text

    def test_empty_findings_section_needs_the_headline(self):
        right = self.clean_yes(HEADLINE_PASSED)
        self.assertEqual(check_report(right) + missing_headline_errors(right), [])
        for filler in ("No findings.", "None.", None):
            with self.subTest(filler=filler):
                text = self.clean_yes(filler)
                self.assertEqual(check_report(text), [])
                self.assertError(missing_headline_errors(text), "needs its headline")
        self.assertError(headline_errors(self.clean_yes(HEADLINE_INCOMPLETE)), "contradicts Ready to merge: Yes")

    def test_needs_verification_does_not_replace_the_headline(self):
        text = with_verdict(drop_block(drop_block(FIXTURE, FINDING_BLOCKS[0]), FINDING_BLOCKS[1]), needs=1)
        self.assertError(missing_headline_errors(text), "needs its headline")
        right = after_first_bullet(text, HEADLINE_INCOMPLETE)
        self.assertEqual(missing_headline_errors(right), [])
        self.assertEqual(missing_headline_errors(compact_form(right)), [])
        self.assertEqual(missing_headline_errors(FIXTURE), [])
        shown = after_first_bullet(with_verdict(no_findings(FIXTURE), warning=1, omitted_warning=1), NO_FINDINGS_SHOWN)
        self.assertEqual(missing_headline_errors(shown), [])

    def test_size_band_must_match_the_diff(self):
        self.assertEqual([size_of(n) for n in (0, 50, 51, 200, 201, 500, 501, 1000, 1001)],
                         ["up to 50", "up to 50", "51 to 200", "51 to 200", "201 to 500", "201 to 500",
                          "501 to 1000", "501 to 1000", "more than 1000"])
        sized = set_line(FIXTURE, "Review effort", SIZED)
        self.assertEqual(check_report(sized), [])
        self.assertEqual(check_report(sized, changed_lines=120), [])
        self.assertError(check_report(sized, changed_lines=711),
                         "Review effort gives 51 to 200 changed lines, but the diff has 711")
        big = set_line(FIXTURE, "Review effort", "**Review effort:** 5/5 — 501 to 1000 changed lines in 2 files; payments.")
        self.assertEqual(check_report(big, changed_lines=711), [])
        why = set_line(FIXTURE, "Review effort", SIZED[:-len("; payments.")] + UNMEASURED + "; payments.")
        self.assertError(check_report(why), "Review effort gives 51 to 200 changed lines, but says the total could not be measured")

    def test_effort_level_follows_size_and_risk_areas(self):
        for line, want in (
                ("**Review effort:** 4/5 — 51 to 200 changed lines in 2 files; payments.",
                 "Review effort is 4/5, but 51 to 200 changed lines with 1 risk area give 3/5"),
                ("**Review effort:** 2/5 — 300 changed lines in 2 files; no risk area.",
                 "Review effort is 2/5, but 300 changed lines with 0 risk areas give 3/5"),
                ("**Review effort:** 3/5 — 300 changed lines in 2 files; payments, no risk area otherwise.",
                 "Review effort is 3/5, but 300 changed lines with 1 risk area give 4/5")):
            with self.subTest(line=line):
                self.assertError(check_report(set_line(FIXTURE, "Review effort", line)), want)
        for line in ("**Review effort:** 3/5 — up to 50 changed lines in 2 files; authorization, personal data, payments.",
                     "**Review effort:** 4/5 — 51 to 200 changed lines in 2 files; the billing flow.",
                     "**Review effort:** 4/5 — 300 changed lines in 2 files; payments, no risk area otherwise."):
            with self.subTest(line=line):
                self.assertEqual(check_report(set_line(FIXTURE, "Review effort", line)), [])

    def test_count_is_checked_on_a_malformed_effort_line(self):
        line = ("**Review effort:** 1/5 — 8 changed lines in 2 files (7 added, 1 removed in src/orders.js; 8 added in "
                "src/routes.js); no risk area.")
        errors = check_report(set_line(FIXTURE, "Review effort", line), changed_lines=16)
        self.assertError(errors, "**Review effort:** line does not match its form")
        self.assertError(errors, "Review effort counts 8 changed lines, but the diff has 16")
        cut = ("**Review effort:** 3/5 — at least 668 changed lines in 2 files (the total could not be measured: output "
               "cut (gh)); payments.")
        errors = check_report(set_line(FIXTURE, "Review effort", cut), changed_lines=711)
        self.assertError(errors, "**Review effort:** line does not match its form")
        self.assertError(errors, "Review effort counts at least 668 changed lines, so its level must be 5/5")
        self.assertError(errors, "Review effort counts at least 668 changed lines, but the diff has 711, a complete "
                                 "measured total")

    def test_semantic_checks_survive_a_malformed_audit(self):
        text = set_line(FIXTURE, "Review effort", "**Review effort:** 4/5 — 668 changed lines in 2 files; no risk area.")
        text = replace_once(text, CONTEXT_LINE, "**Read for context:** 0 files: none. I used `git show` to read "
                            "`src/orders.js`.")
        errors = check_report(text, changed_lines=711)
        self.assertError(errors, "**Read for context:** line is malformed")
        self.assertError(errors, "Review effort counts 668 changed lines, but the diff has 711")

    def test_context_checks_survive_another_malformed_audit_line(self):
        text = replace_once(FIXTURE, CHECKED, "**Checked with no findings:** Architecture and Code & File Size, as far "
                            "as I can tell")
        text = replace_once(text, CONTEXT_LINE, "**Read for context:** 3 files: `package.json`, `src/orders.js`.")
        errors = check_report(text)
        self.assertError(errors, "**Checked with no findings:** line is malformed")
        self.assertError(errors, "Read for context lists 2 paths but counts 3")
        self.assertError(errors, "Read for context names `src/orders.js`, which is a changed file")

    def test_every_defect_of_one_report_is_reported(self):
        text = set_line(self.clean_yes("No findings."), "Review effort",
                        "**Review effort:** 1/5 — 6 changed lines in 2 files; no risk area.")
        text = replace_once(text, CONTEXT_LINE, "**Read for context:** 2 files: `composer.json`, `package.json`, "
                            "`tests/orders.test.js`.")
        errors = check_report(text, changed_lines=7) + missing_headline_errors(text)
        self.assertError(errors, "needs its headline")
        self.assertError(errors, "Read for context lists 3 paths but counts 2")
        self.assertError(errors, "Review effort counts 6 changed lines, but the diff has 7")

    def test_context_line_without_a_count(self):
        bare = replace_once(FIXTURE, CONTEXT_LINE, BARE_CONTEXT)
        self.assertEqual(check_report(bare), [])
        self.assertIn("; 2 files read for context;", compact_audit_line(parse_audit(bare)))
        dup = replace_once(FIXTURE, CONTEXT_LINE, "**Read for context:** `package.json`, `package.json`.")
        self.assertError(check_report(dup), "Read for context paths must be unique and in alphabetical order")
        changed = replace_once(FIXTURE, CONTEXT_LINE, "**Read for context:** `package.json`, `src/routes.js`.")
        self.assertError(check_report(changed), "Read for context names `src/routes.js`, which is a changed file")

    def test_effort_line_states_only_the_final_values(self):
        for line, wants in (
                ("**Review effort:** 2/5 — 51 to 200 changed lines is wrong here; the diff has 13 changed lines, so the "
                 "size is up to 50 changed lines in 2 files; payments. Level: 1 + 1 = 2/5.",
                 ("Review effort names different sizes: 51 to 200, up to 50",)),
                ("**Review effort:** 1/5 — up to 50 changed lines in 2 files; payments (adds 1 to the level, giving 2/5).",
                 ("Review effort states different levels: 1/5, 2/5",
                  "Review effort is 1/5, but up to 50 changed lines with 1 risk area give 2/5")),
                ("**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments (giving 3/5).",
                 ("Review effort states different levels: 2/5, 3/5",)),
                ("**Review effort:** 1/5 + 1 — up to 50 changed lines in 2 files; payments. Level: 2/5.",
                 ("Review effort states different levels: 1/5, 2/5",))):
            errors = check_report(set_line(FIXTURE, "Review effort", line))
            for want in wants:
                with self.subTest(line=line, want=want):
                    self.assertError(errors, want)
        for line in ("**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.",
                     "**Review effort:** 5/5 — at least 400 changed lines in 2 files" + UNMEASURED + "; payments."):
            with self.subTest(line=line):
                self.assertEqual(check_report(set_line(FIXTURE, "Review effort", line)), [])
        same = "**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments (adds 1 to the level, giving 2/5)."
        self.assertEqual([e for e in check_report(set_line(FIXTURE, "Review effort", same)) if "different" in e], [])


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

    def test_skill_table_gives_effort_level(self):
        table = effort_table(SKILL)
        self.assertEqual(list(table), list(SIZES))
        for n in (0, 50, 51, 200, 201, 500, 501, 1000, 1001):
            with self.subTest(changed_lines=n):
                self.assertEqual(table[size_of(n)], tuple(effort_level(n, r) for r in (0, 1, 2)))
                self.assertEqual(table[size_of(n)][2], effort_level(n, 3))
        drifted = SKILL.replace("| `51 to 200` | 2/5 | 3/5 | 4/5 |", "| `51 to 200` | 2/5 | 2/5 | 4/5 |")
        self.assertNotEqual(effort_table(drifted), table)


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
        full = replace_once(example_full(), "`skill:references/observability.md`, ",
                            "`skill:references/observability.md`, `skill:references/publishing.md`, ")
        self.assertEqual(check_report(full), [])
        compact = compact_audit_line(parse_audit(full))
        self.assertIn("; 11 files read for context;", compact)
        intro = EXAMPLE[EXAMPLE.index("## Publishing Dry Run"):EXAMPLE.index("## Dry run — nothing was published")]
        self.assertIn("`skill:references/publishing.md`", intro)
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


SECURITY_DIM = ("security dimension", "dimension not reviewed")
SECURITY_DIM_ITEM = ("- security dimension — dimension not reviewed, material: the security subagent stopped without a "
                     "result, and the changed query in `src/orders.js` was not checked for injection.")


class DimensionTests(Base):
    """The dimension review limit of references/dimensions.md, as Step 3 of SKILL.md lists it."""

    def test_dimension_table_owns_every_category_once(self):
        owners = dimension_owners(DIMENSIONS)
        self.assertEqual(list(owners), ["bugs", "security", "repository rules", "tests", "coordinator"])
        self.assertEqual(owners["repository rules"], ())
        self.assertEqual(sorted(cat for cats in owners.values() for cat in cats), sorted(CATEGORIES))

    def test_skill_lists_every_audit_tag(self):
        for tag in TAGS:
            self.assertIn(f"  - `{tag}`: ", SKILL)

    def test_material_dimension_item_blocks(self):
        text = with_items(no_findings(FIXTURE), SECURITY_DIM_ITEM)
        self.assertEqual(check_report(with_verdict(text, material=[SECURITY_DIM])), [])
        self.assertError(check_report(with_verdict(text)), "Ready to merge line is")

    def test_nonmaterial_dimension_item_does_not_block(self):
        text = with_items(no_findings(FIXTURE), "- repository rules dimension — dimension not reviewed, not material: the "
                          "subagent stopped without a result, and the only changed lines it would check are comments.")
        self.assertEqual(check_report(with_verdict(text)), [])

    def test_unreviewed_dimension_category_is_not_clean(self):
        text = with_items(no_findings(FIXTURE), SECURITY_DIM_ITEM)
        text = set_line(text, "Checked with no findings", "**Checked with no findings:** Security, Architecture, "
                        "Code & File Size.")
        self.assertError(check_report(with_verdict(text, material=[SECURITY_DIM])),
                         "names Security, but its dimension was not reviewed")

    def test_dimension_item_must_name_a_subagent_dimension(self):
        text = with_items(no_findings(FIXTURE), "- tests dimension — dimension not reviewed, not material: the "
                          "subagent stopped without a result.")
        self.assertError(check_report(with_verdict(text)), "it must be the bugs, security or repository rules dimension")


if __name__ == "__main__":
    unittest.main()
