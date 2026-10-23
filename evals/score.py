"""Parse and score code review reports produced by the eval runner."""

from __future__ import annotations

import re

SEVERITIES = ("Suggestion", "Warning", "Critical")

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HEADING_SEVERITY_RE = re.compile(r"\b(critical|warning|suggestion)s?\b", re.I)
_BODY_SEVERITY_RE = re.compile(r"\bseverity\b\W*(critical|warning|suggestion)", re.I)
_DETAIL_RE = re.compile(r"^\W*(?:file|issue|location)s?\W*:", re.I)
_VERIFICATION_HEADING_RE = re.compile(r"\bneeds\s+human\s+verification\b", re.I)
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


def parse_findings(report: str) -> list[dict]:
    """Return the findings in ``report`` order as heading/severity/text dicts.

    ``needs_verification`` is True for findings nested under a "Needs human
    verification" heading (Medium confidence); scoring ignores them.
    ``compact`` is True for one-line findings (``path:line: Severity: problem → fix``).
    """
    blocks = []
    # Lines before the first heading belong to a level-0 block that only holds compact findings.
    current = {"line": "", "heading": "", "level": 0, "body": [], "compact": [], "preamble": True}
    in_fence = False

    for line in report.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            current["body"].append(line)
            continue

        match = None if in_fence else _HEADING_RE.match(line)
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

        compact_match = None if in_fence else _COMPACT_RE.match(line)
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
        stack.append((block["level"], own_severity, needs_verification))

        severity = own_severity
        if severity is None:
            for body_line in block["body"]:
                body_match = _BODY_SEVERITY_RE.search(body_line)
                if body_match is not None:
                    severity = _NORMALIZED_SEVERITY[body_match.group(1).lower()]
                    break
        if severity is None:
            for _level, inherited, _verify in reversed(stack[:-1]):
                if inherited is not None:
                    severity = inherited
                    break

        has_detail = any(_DETAIL_RE.match(body_line) for body_line in block["body"])
        if not block["preamble"] and severity is not None and has_detail:
            findings.append({
                "heading": block["heading"],
                "severity": severity,
                "needs_verification": needs_verification,
                "compact": False,
                "text": block["line"] + "\n" + "\n".join(block["body"]),
            })
        for m in block["compact"]:
            findings.append({
                "heading": m.group("item"),
                "severity": _NORMALIZED_SEVERITY[m.group("severity").lower()],
                "text": m.group("item"),
                "needs_verification": needs_verification,
                "compact": True,
            })

    return findings


def score_bug(report: str, patterns: list[str], min_severity: str) -> dict:
    """Report whether one main-list finding at ``min_severity`` or above matches every pattern."""
    minimum = SEVERITIES.index(min_severity)
    for finding in parse_findings(report):
        if finding["needs_verification"]:
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
        if not finding["needs_verification"] and finding["severity"] in ("Warning", "Critical")
    )
    return {"false_positives": false_positives}


def looks_like_report(report: str) -> bool:
    """Return True when the output is a review report, not a question or echo."""
    if parse_findings(report):
        return True

    in_fence = False
    for line in report.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and PASSED_LINE.match(line):
            return True
    return False


def stack_mentioned(report: str, stack: str) -> bool:
    """Return True when ``stack`` appears as a whole word in the report."""
    return re.search(r"\b" + re.escape(stack) + r"\b", report, re.I) is not None
