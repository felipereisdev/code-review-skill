"""Parse and score code review reports produced by the eval runner."""

from __future__ import annotations

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

_NORMALIZED_SEVERITY = {
    "critical": "Critical",
    "warning": "Warning",
    "suggestion": "Suggestion",
}


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


def score_bug(report: str, patterns: list[str], min_severity: str) -> dict:
    """Report whether one main-list finding at ``min_severity`` or above matches every pattern."""
    minimum = SEVERITIES.index(min_severity)
    for finding in parse_findings(report):
        if finding["needs_verification"] or finding["pre_existing"] or finding["already_raised"]:
            continue
        if SEVERITIES.index(finding["severity"]) < minimum:
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
    for line in report.splitlines():
        in_fence = fence is not None
        fence = _active_fence(line, fence)
        if not in_fence and fence is None and PASSED_LINE.match(line):
            return True
    return False


def stack_mentioned(report: str, stack: str) -> bool:
    """Return True when ``stack`` appears as a whole word in the report."""
    return re.search(r"\b" + re.escape(stack) + r"\b", report, re.I) is not None
