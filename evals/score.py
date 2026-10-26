"""Parse and score code review reports produced by the eval runner."""

from __future__ import annotations

import json
import re

SEVERITIES = ("Suggestion", "Warning", "Critical")

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HEADING_SEVERITY_RE = re.compile(r"\b(critical|warning|suggestion)s?\b", re.I)
_BODY_SEVERITY_RE = re.compile(r"\bseverity\b\W*(critical|warning|suggestion)", re.I)
_DETAIL_RE = re.compile(r"^\W*(?:file|issue|location)s?\W*:", re.I)
_VERIFICATION_HEADING_RE = re.compile(r"\bneeds\s+human\s+verification\b", re.I)
_PRE_EXISTING_HEADING_RE = re.compile(
    r"^[\W_]*pre[- ]?existing\s+(?:issues?|problems?)[\W_]*"
    r"(?:\(\s*not\s+counted\s*\)|[—–-]+\s*not\s+counted)?[\W_]*$",
    re.I,
)
_ALREADY_RAISED_HEADING_RE = re.compile(r"^[\W_]*already\s+raised\b", re.I)
_FENCE_RE =re.compile(r"^ {0,3}(`{3,}|~{3,})")
_COMPACT_RE = re.compile(
    r"^\s*(?:[-*]\s+)?"
    r"(?P<item>(?:`(?=[^`]*[A-Za-z])[^`]+:\d+(?:-\d+)?`"
    r"|(?=[^\s`:|]*[A-Za-z])[^\s`:|]+:\d+(?:-\d+)?)"
    r":\s*\**(?P<severity>critical|warning|suggestion)\**\s*:\s*\S.*?)\s*$",
    re.I,
)
PASSED_LINE = re.compile(
    r"^[\s*_\"'>]*code review passed\s*[—–-]{1,2}\s*no issues found\.?[\s*_\"']*$",
    re.I,
)
# The headline of a report with no listed finding whose Ready to merge is not Yes (SKILL.md Step 3).
INCOMPLETE_LINE = re.compile(
    r"^[\s*_]*review incomplete or pending\s*[—–-]{1,2}\s*no confirmed findings in the code inspected\.?[\s*_]*$",
    re.I,
)
# Discovery-only recognizers: a blockquote marker or literal quote makes the line template data, not metadata.
_READY_LINE_RE = re.compile(r"^[\s*_]*ready to merge:[\s*_]*(yes|no|with fixes)\b", re.I)
_AUDIT_LINE_RE = re.compile(r"^(?:#{1,6}\s*audit\s*#*\s*$|[\s*_]*audit:)", re.I)
_FILE_LOCATION_RE = re.compile(r"^\W*(?:file|location)s?\W*:[\s*_]*(?P<value>.*)$", re.I)
_LOCATION_TOKEN_RE = re.compile(r"`([^`]+)`|([^\s`:|]+)")
_LINE_SUFFIX_RE = re.compile(r":\d+(?:-\d+)?$")

_NORMALIZED_SEVERITY = {
    "critical": "Critical",
    "warning": "Warning",
    "suggestion": "Suggestion",
}

_READY_VALUES = {"yes": "Yes", "no": "No", "with fixes": "With fixes"}


def _normalize_severity(match: re.Match | None) -> str | None:
    if match is None:
        return None
    return _NORMALIZED_SEVERITY[match.group(1).lower()]


def _active_fence(line: str, fence: str | None) -> str | None:
    """Return the Markdown code fence active after ``line``.

    Recognizes backtick and tilde fences indented by up to three spaces and
    tracks the opening delimiter, so a fence only ends at the matching
    character with at least the same length and no info string.
    """
    match = _FENCE_RE.match(line)
    if match is None:
        return fence
    marker = match.group(1)
    if fence is None:
        return marker
    if marker[0] != fence[0] or len(marker) < len(fence) or line[match.end():].strip():
        return fence
    return None


def _outside_fences(report: str) -> list[str]:
    """Return the lines of ``report`` that are not inside a code fence."""
    fence = None
    outside = []
    for line in report.splitlines():
        in_fence = fence is not None
        fence = _active_fence(line, fence)
        if in_fence or fence is not None:
            continue
        outside.append(line)
    return outside


def parse_findings(report: str) -> list[dict]:
    """Return the findings in ``report`` order as heading/severity/text dicts.

    ``needs_verification`` is True for findings nested under a "Needs human
    verification" heading (Medium confidence); scoring ignores them.
    ``pre_existing`` is True for findings nested under a "Pre-existing issues" heading; scoring ignores them.
    ``already_raised`` is True for findings nested under an "Already raised in the PR" heading; scoring ignores them.
    ``compact`` is True for one-line findings (``path:line: Severity: problem → fix``).
    """
    blocks = []
    # Lines before the first heading belong to a level-0 block that only holds compact findings.
    current = {"line": "", "heading": "", "level": 0, "body": [], "compact": [], "preamble": True}
    fence = None

    for line in report.splitlines():
        in_fence = fence is not None
        fence = _active_fence(line, fence)
        if in_fence or fence is not None:
            current["body"].append(line)
            continue

        match = _HEADING_RE.match(line)
        if match is not None:
            blocks.append(current)
            current = {
                "line": line,
                "heading": match.group(2).strip(),
                "level": len(match.group(1)),
                "body": [],
                "compact": [],
                "preamble": False,
            }
        else:
            current["body"].append(line)

        compact_match = _COMPACT_RE.match(line)
        if compact_match is not None:
            current["compact"].append(compact_match)

    blocks.append(current)

    findings = []
    stack = []

    for block in blocks:
        own_severity = _normalize_severity(_HEADING_SEVERITY_RE.search(block["heading"]))

        while stack and stack[-1][0] >= block["level"]:
            stack.pop()
        needs_verification = bool(_VERIFICATION_HEADING_RE.search(block["heading"])) or (
            bool(stack) and stack[-1][2]
        )
        pre_existing = bool(_PRE_EXISTING_HEADING_RE.search(block["heading"])) or (
            bool(stack) and stack[-1][3]
        )
        already_raised = bool(_ALREADY_RAISED_HEADING_RE.search(block["heading"])) or (
            bool(stack) and stack[-1][4]
        )
        stack.append((block["level"], own_severity, needs_verification, pre_existing, already_raised))

        severity = own_severity
        if severity is None:
            for body_line in block["body"]:
                body_match = _BODY_SEVERITY_RE.search(body_line)
                if body_match is not None:
                    severity = _NORMALIZED_SEVERITY[body_match.group(1).lower()]
                    break
        if severity is None:
            for _level, inherited, _verify, _pre, _raised in reversed(stack[:-1]):
                if inherited is not None:
                    severity = inherited
                    break

        has_detail = any(_DETAIL_RE.match(body_line) for body_line in block["body"])
        if not block["preamble"] and severity is not None and has_detail:
            findings.append({
                "heading": block["heading"],
                "severity": severity,
                "needs_verification": needs_verification,
                "pre_existing": pre_existing,
                "already_raised": already_raised,
                "compact": False,
                "text": block["line"] + "\n" + "\n".join(block["body"]),
            })
        for m in block["compact"]:
            findings.append({
                "heading": m.group("item"),
                "severity": _NORMALIZED_SEVERITY[m.group("severity").lower()],
                "text": m.group("item"),
                "needs_verification": needs_verification,
                "pre_existing": pre_existing,
                "already_raised": already_raised,
                "compact": True,
            })

    return findings


def _location_path(value: str) -> str | None:
    """Return the path at the start of ``value``, without its line or range suffix."""
    match = _LOCATION_TOKEN_RE.match(value)
    if match is None:
        return None
    return _LINE_SUFFIX_RE.sub("", match.group(1) or match.group(2))


def _actual_locations(finding: dict) -> list[str | None]:
    """Return the paths that name where ``finding`` is located.

    A compact finding is located by its leading path. A block finding is located by its
    File or Location field outside code fences, so a path in Issue, Evidence, Fix or History does not count.
    """
    if finding["compact"]:
        return [_location_path(finding["text"])]
    locations = []
    for line in _outside_fences(finding["text"]):
        match = _FILE_LOCATION_RE.match(line)
        if match is not None:
            locations.append(_location_path(match.group("value")))
    return locations


def score_bug(report: str, patterns: list[str], min_severity: str, location_path: str | None = None) -> dict:
    """Report whether one main-list finding at ``min_severity`` or above matches every pattern.

    When ``location_path`` is given, the matching finding must also be located at that path.
    """
    minimum = SEVERITIES.index(min_severity)
    for finding in parse_findings(report):
        if finding["needs_verification"] or finding["pre_existing"] or finding["already_raised"]:
            continue
        if SEVERITIES.index(finding["severity"]) < minimum:
            continue
        if location_path is not None and location_path not in _actual_locations(finding):
            continue
        if all(re.search(pattern, finding["text"], re.I) for pattern in patterns):
            return {"detected": True, "matched_finding": finding["heading"]}
    return {"detected": False, "matched_finding": None}


def score_clean(report: str) -> dict:
    """Count main-list findings severe enough to be false positives on a clean diff."""
    false_positives = sum(
        1 for finding in parse_findings(report)
        if not finding["needs_verification"] and not finding["pre_existing"]
        and not finding["already_raised"] and finding["severity"] in ("Warning", "Critical")
    )
    return {"false_positives": false_positives}


def looks_like_report(report: str) -> bool:
    """Return True when the output is a review report, not a question or echo."""
    if parse_findings(report):
        return True

    fence = None
    outside = []
    for line in report.splitlines():
        in_fence = fence is not None
        fence = _active_fence(line, fence)
        if in_fence or fence is not None:
            continue
        if PASSED_LINE.match(line):
            return True
        outside.append(line)
    return _incomplete_report(outside)


def _incomplete_report(lines: list[str]) -> bool:
    """Return True for the incomplete headline beside a Ready to merge line that is not Yes, and an Audit."""
    readiness = {m.group(1).lower() for m in map(_READY_LINE_RE.match, lines) if m}
    return (any(INCOMPLETE_LINE.match(line) for line in lines)
            and bool(readiness) and "yes" not in readiness
            and any(_AUDIT_LINE_RE.match(line) for line in lines))


def report_completeness(report: str) -> dict:
    """Describe whether ``report`` is a finished review, not one cut off or left incomplete.

    The verdict cannot tell an incomplete review that still lists findings (rows 1 and 3)
    from a complete one (row 2), so those reports count as complete.
    """
    lines = _outside_fences(report)
    readiness = [m.group(1).lower() for m in map(_READY_LINE_RE.match, lines) if m]
    ready = _READY_VALUES[readiness[-1]] if readiness else None
    audit = any(_AUDIT_LINE_RE.match(line) for line in lines)
    incomplete = any(INCOMPLETE_LINE.match(line) for line in lines)
    return {
        "ready_to_merge": ready,
        "audit": audit,
        "incomplete_headline": incomplete,
        "complete": looks_like_report(report) and ready is not None and audit and not incomplete,
    }


def observations(report: str, meta: dict) -> dict:
    """Record whether the report states its intent and cites the spec or history labels.

    These facts never change a score.
    """
    intent = [line for line in _outside_fences(report) if line.lstrip("*_ ").startswith("Intent:")]
    main = [
        finding for finding in parse_findings(report)
        if not (finding["needs_verification"] or finding["pre_existing"] or finding["already_raised"])
    ]
    spec_path = meta.get("spec_path")
    return {
        "intent_line": bool(intent),
        "spec_cited": None if not spec_path else any(spec_path in line for line in intent),
        "history_cited": None if not meta.get("history") else any("History:" in f["text"] for f in main),
    }


def stack_mentioned(report: str, stack: str) -> bool:
    """Return True when ``stack`` appears as a whole word in the report."""
    return re.search(r"\b" + re.escape(stack) + r"\b", report, re.I) is not None


FIX_QUESTION = "Which of these fixes should I apply?"
_SECOND_OPINION_REASONS = (
    "{cli} is not installed",
    "the call was refused",
    "{cli} cannot be limited to the supplied content",
    "the reviewed snapshot is not the current one",
)


def _plain(line: str) -> str:
    return line.strip().strip("*_").strip()


def _heading_texts(lines: list[str]) -> list[str]:
    return [match.group(2) for match in map(_HEADING_RE.match, lines) if match]


def check_json_control(stdout: str, gate_exit: int | None, expect: dict) -> dict:
    """Check a --format json review: one valid document whose gate result and Critical findings match ``expect``."""
    valid = gate_exit in (0, 1, 2)
    doc = json.loads(stdout) if valid else None
    review = doc.get("review") if doc is not None else None
    criticals = []
    if isinstance(review, dict):
        criticals = [finding.get("path") for finding in review.get("findings", [])
                     if finding.get("severity") == "Critical"]

    checks = {"document_valid": valid, "gate_exit": gate_exit == expect["gate_exit"]}
    if doc is None:
        checks.update(status=False, gate_status=False, critical_path=False)
    else:
        checks["status"] = doc.get("status") == expect["status"]
        checks["gate_status"] = (doc.get("gate") or {}).get("status") == expect["gate_status"]
        if expect["critical_path"] is None:
            checks["critical_path"] = not criticals
        else:
            checks["critical_path"] = expect["critical_path"] in criticals
    return {
        "checks": checks,
        "report_valid": valid,
        "complete": doc is not None and doc.get("status") == "complete",
    }


def check_fix_control(stdout: str, expect: dict) -> dict:
    """Check a headless --fix run: a complete report with a fix proposal, the stop line and no question."""
    lines = _outside_fences(stdout)
    headings = _heading_texts(lines)
    report = looks_like_report(stdout)
    complete = report_completeness(stdout)["complete"]
    checks = {
        "report": report,
        "complete": complete,
        "proposal": "Fix proposal" in headings,
        "stop_line": any(_plain(line) == expect["stop_line"] for line in lines),
        "no_question": FIX_QUESTION not in stdout,
        "no_fix_section": "Fix" not in headings,
    }
    return {"checks": checks, "report_valid": report, "complete": complete}


def check_second_opinion_control(stdout: str, expect: dict) -> dict:
    """Check that a report states the second opinion as unavailable and never as having run."""
    cli = expect["cli"]
    reasons = "|".join(re.escape(reason.format(cli=cli)) for reason in _SECOND_OPINION_REASONS)
    unavailable = re.compile(
        r"^\s*\*\*Second opinion:\*\*\s+" + re.escape(cli) + r" unavailable: (?:" + reasons + r")\.\s*$"
    )
    other = re.compile(r"^\s*\*\*Second opinion:\*\*\s+\S+\s+(?:returned|failed)\b")
    lines = _outside_fences(stdout)
    report = looks_like_report(stdout)
    complete = report_completeness(stdout)["complete"]
    checks = {
        "report": report,
        "complete": complete,
        "unavailable_line": sum(1 for line in lines if unavailable.match(line)) == 1,
        "no_other_outcome": not any(other.match(line) for line in lines),
    }
    return {"checks": checks, "report_valid": report, "complete": complete}
