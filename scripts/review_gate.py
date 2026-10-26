#!/usr/bin/env python3
"""Optional consumer of the code-review skill's --format json document: validates it and exits with the gate status.

Usage: python3 scripts/review_gate.py [FILE|-]   (no FILE or - reads standard input)
Exit: 0 pass, 1 fail (verified Critical), 2 incomplete or error, 3 invalid input.
The skill never needs this script; it shows how a CI job turns the document into a real exit status.
"""
from __future__ import annotations

import json
import re
import sys

SCHEMA = "code-review-skill/review"
VERSION = 1
STATUSES = ("complete", "nothing_to_review", "error")
GATE_STATUSES = ("pass", "fail", "incomplete", "error", "not_requested")
TOP_KEYS = ("schema", "version", "status", "message", "scope", "gate", "review")
GATE_KEYS = ("fail_on", "status", "reason")
REVIEW_KEYS = ("context_lines", "intent", "findings", "needs_verification", "pre_existing", "already_raised",
               "verification", "omitted_by_configuration", "triage", "verdict", "audit")
FINDING_KEYS = ("category", "severity", "confidence", "location", "path", "side", "start_line", "end_line", "rule",
                "also_at", "issue", "evidence", "fix", "omitted_by")
TRIAGE_KEYS = ("review_effort", "relevant_tests", "look_first", "ready_to_merge")
AUDIT_KEYS = ("files_reviewed", "read_for_context", "checked_with_no_findings", "already_raised_not_verified",
              "not_verified")
CATEGORIES = ("Security", "Performance", "Tests/Coverage", "Architecture", "Code & File Size", "Potential Bugs",
              "Accessibility", "Observability", "API Design", "Resilience", "DB Migrations", "Concurrency", "i18n",
              "Privacy/Compliance", "Architecture Patterns", "Stack-Specific")
SEVERITIES = ("Critical", "Warning", "Suggestion")
FILTERS = ("min_severity", "disabled_categories", "max_findings_per_file")
TAGS = ("not read", "binary", "context not read", "API not validated", "tests not verified", "dimension not reviewed")
ROW_VALUES = {1: "No", 2: "No", 3: "No", 4: "With fixes", 5: "With fixes", 6: "With fixes", 7: "Yes"}
GUIDE = "skill:references/json-output.md"
LOCATION_RE = re.compile(r"^.+:\d+(?:-\d+)?$")
RULE_RE = re.compile(r"^\S+:L\d+(?:-L\d+)?$")
EXCLUDED_RE = re.compile(r"^\*\*Excluded by configuration:\*\* (\d+) changed files? match(?:es)? ignore_paths and "
                         r"(?:was|were) not reviewed: (.+)\.$")
MORE_RE = re.compile(r", and (\d+) more$")
BINARY_RE = re.compile(r"^`([^`]+)`$")
WHOLE_RE = re.compile(r"^`([^`]+)` \(whole file\)$")
PART_RE = re.compile(r"^`([^`]+)` lines \d+-\d+$")
EXIT = {"pass": 0, "fail": 1, "incomplete": 2, "error": 2}
INVALID = 3


class GateInputError(Exception):
    """The input is not one JSON document of the contract."""


def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise GateInputError(f'duplicate key "{key}"')
        seen[key] = value
    return seen


def _no_constant(name):
    raise GateInputError(f"{name} is not valid JSON")


def load(data: bytes) -> dict:
    """Parses the whole input as exactly one JSON object; anything else raises GateInputError."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise GateInputError("the input is not UTF-8 text") from None
    if not text.strip():
        raise GateInputError("empty input: no JSON document")
    try:
        doc = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except json.JSONDecodeError as exc:
        raise GateInputError(f"not a single JSON document: {exc.msg} at line {exc.lineno} column {exc.colno}") from None
    except (ValueError, RecursionError):
        raise GateInputError("not a single JSON document: it nests too deeply or holds a number too long to read") \
            from None
    if not isinstance(doc, dict):
        raise GateInputError("the document is not a JSON object")
    return doc


def _is_int(value) -> bool:
    return type(value) is int


def _is_text(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _keys(errors, name, value, keys) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return False
    if set(value) != set(keys):
        missing = [k for k in keys if k not in value]
        extra = sorted(k for k in value if k not in keys)
        errors.append(f"{name} keys: missing {missing}, unexpected {extra}")
        return False
    return True


def _text_list(errors, name, value) -> bool:
    if not isinstance(value, list) or not all(_is_text(item) for item in value):
        errors.append(f"{name} must be a list of non-empty strings")
        return False
    return True


def _finding_errors(errors, name, finding, confidence):
    if not _keys(errors, name, finding, FINDING_KEYS):
        return
    if finding["category"] not in CATEGORIES:
        errors.append(f"{name}.category is not a Summary table category: {finding['category']!r}")
    if finding["severity"] not in SEVERITIES:
        errors.append(f"{name}.severity must be one of {', '.join(SEVERITIES)}")
    if finding["confidence"] != confidence:
        errors.append(f'{name}.confidence must be "{confidence}"')
    if finding["side"] not in ("new", "old"):
        errors.append(f'{name}.side must be "new" or "old"')
    start, end = finding["start_line"], finding["end_line"]
    if not (_is_int(start) and _is_int(end) and 1 <= start <= end):
        errors.append(f"{name}.start_line and end_line must be whole numbers with 1 <= start_line <= end_line")
    elif not _is_text(finding["path"]):
        errors.append(f"{name}.path must be a non-empty string")
    else:
        lines = str(start) if start == end else f"{start}-{end}"
        if finding["location"] != f"{finding['path']}:{lines}":
            errors.append(f"{name}.location must be {finding['path']}:{lines}")
    if finding["rule"] is not None and not (isinstance(finding["rule"], str) and RULE_RE.match(finding["rule"])):
        errors.append(f"{name}.rule must be null or path:Lstart-Lend")
    also = finding["also_at"]
    if not isinstance(also, list) or not all(isinstance(p, str) and LOCATION_RE.match(p) for p in also):
        errors.append(f"{name}.also_at must be a list of path:line or path:start-end places")
    elif len(set(also)) != len(also) or finding["location"] in also:
        errors.append(f"{name}.also_at repeats a place: a grouped finding lists each other place once")
    for key in ("issue", "evidence", "fix"):
        if not _is_text(finding[key]):
            errors.append(f"{name}.{key} must be a non-empty string")
    if finding["omitted_by"] is not None and finding["omitted_by"] not in FILTERS:
        errors.append(f"{name}.omitted_by must be null or one of {', '.join(FILTERS)}")
    if finding["severity"] == "Critical" and finding["omitted_by"] is not None:
        errors.append(f"{name}: a Critical finding is never omitted by a filter")


def _audit_errors(errors, audit):
    if not _keys(errors, "review.audit", audit, AUDIT_KEYS):
        return
    files = audit["files_reviewed"]
    if _keys(errors, "review.audit.files_reviewed", files, ("reviewed", "changed", "paths")):
        paths = files["paths"]
        if not (_is_int(files["reviewed"]) and _is_int(files["changed"]) and 0 <= files["reviewed"] <= files["changed"]):
            errors.append("review.audit.files_reviewed: reviewed and changed must be whole numbers, reviewed <= changed")
        elif not isinstance(paths, list) or not all(_is_text(p) for p in paths) or len(paths) != files["reviewed"] \
                or len(set(paths)) != len(paths):
            errors.append("review.audit.files_reviewed.paths must list each reviewed path once")
    context = audit["read_for_context"]
    if _text_list(errors, "review.audit.read_for_context", context):
        if len(set(context)) != len(context):
            errors.append("review.audit.read_for_context lists a file twice")
        if GUIDE not in context:
            errors.append(f"review.audit.read_for_context must list {GUIDE}")
    clean = audit["checked_with_no_findings"]
    if not isinstance(clean, list) or not all(c in CATEGORIES for c in clean):
        errors.append("review.audit.checked_with_no_findings must list Summary table categories")
    raised = audit["already_raised_not_verified"]
    if raised is not None:
        if not isinstance(raised, list):
            errors.append("review.audit.already_raised_not_verified must be null or a list")
        else:
            for i, entry in enumerate(raised):
                name = f"review.audit.already_raised_not_verified[{i}]"
                if _keys(errors, name, entry, ("location", "category")) and not (
                        isinstance(entry["location"], str) and LOCATION_RE.match(entry["location"])
                        and entry["category"] in CATEGORIES):
                    errors.append(f"{name} needs a path:line location and a Summary table category")
    items = audit["not_verified"]
    if not isinstance(items, list):
        errors.append("review.audit.not_verified must be a list")
    else:
        for i, item in enumerate(items):
            name = f"review.audit.not_verified[{i}]"
            if _keys(errors, name, item, ("what", "tag", "material", "detail")) and not (
                    _is_text(item["what"]) and item["tag"] in TAGS and isinstance(item["material"], bool)
                    and _is_text(item["detail"])):
                errors.append(f"{name} needs what, a known tag, material true or false, and detail")


def _accounting_errors(errors, review):
    """SKILL.md Audit: the reviewed, excluded, binary and whole-file unread files add up to <m>, each counted once."""
    start = len(errors)
    audit = review["audit"]
    files = audit["files_reviewed"]
    reviewed = files["paths"]
    excluded_count, excluded = 0, []
    lines = [line for line in review["context_lines"] if line.startswith("**Excluded by configuration:** ")]
    if len(lines) > 1:
        errors.append("review.context_lines has more than one **Excluded by configuration:** line")
        return
    if lines:
        match = EXCLUDED_RE.match(lines[0])
        if match is None:
            errors.append("review.context_lines: the **Excluded by configuration:** line must count and list the "
                          "excluded files as references/configuration.md writes it")
            return
        excluded_count = int(match.group(1))
        excluded = re.findall(r"`([^`]+)`", match.group(2))
        more = MORE_RE.search(match.group(2))
        listed = len(excluded) + (int(more.group(1)) if more else 0)
        if excluded_count == 0 or listed != excluded_count:
            errors.append(f"review.context_lines: the **Excluded by configuration:** line counts {excluded_count} "
                          f"files and lists {listed}")
            return
    binary, unread = [], []
    for i, item in enumerate(audit["not_verified"]):
        name = f"review.audit.not_verified[{i}]"
        if item["tag"] == "binary":
            match = BINARY_RE.match(item["what"])
            if match is None:
                errors.append(f"{name}.what of a binary item must be `<path>`")
            else:
                binary.append(match.group(1))
        elif item["tag"] == "not read":
            whole, part = WHOLE_RE.match(item["what"]), PART_RE.match(item["what"])
            if whole is not None:
                unread.append(whole.group(1))
            elif part is None:
                errors.append(f"{name}.what of a not read item must be `<path>` (whole file) or `<path>` lines <a>-<b>")
            elif part.group(1) not in reviewed:
                errors.append(f"{name}: {item['what']} are unread lines of a file that is not reviewed")
    if len(errors) > start:
        return
    counted = reviewed + excluded + binary + unread
    twice = sorted({path for path in counted if counted.count(path) > 1})
    if twice:
        errors.append(f"review.audit counts {', '.join(twice)} more than once among the reviewed, excluded, binary "
                      "and whole-file unread files")
        return
    total = len(reviewed) + excluded_count + len(binary) + len(unread)
    if total != files["changed"]:
        errors.append(f"review.audit.files_reviewed: {len(reviewed)} reviewed + {excluded_count} excluded by "
                      f"configuration + {len(binary)} binary + {len(unread)} not read as a whole make {total}, "
                      f"not the {files['changed']} changed files")
    in_context = [path for path in audit["read_for_context"] if path in counted]
    if in_context:
        errors.append(f"review.audit.read_for_context lists a changed file: {', '.join(in_context)}")


def expected_row(review: dict) -> int:
    """The verdict row of SKILL.md Step 3 from the facts, counting findings before the configuration filters."""
    findings, needs, audit = review["findings"], review["needs_verification"], review["audit"]
    if audit["files_reviewed"]["reviewed"] == 0:
        return 1
    if any(f["severity"] == "Critical" for f in findings):
        return 2
    if any(item["material"] for item in audit["not_verified"]):
        return 3
    if any(f["severity"] == "Warning" for f in findings):
        return 4
    if any(f["severity"] in ("Critical", "Warning") for f in needs):
        return 5
    if audit["already_raised_not_verified"]:
        return 6
    return 7


def expected_gate(doc: dict) -> str:
    """The gate status that references/json-output.md gives for the facts of a valid document."""
    if doc["status"] == "error":
        return "error"
    if doc["gate"]["fail_on"] is None:
        return "not_requested"
    if doc["status"] == "nothing_to_review":
        return "pass"
    row = expected_row(doc["review"])
    if row == 2:
        return "fail"
    if row in (1, 3):
        return "incomplete"
    return "pass"


def contract_errors(doc: dict) -> list:
    """The contract errors of references/json-output.md that this script can check; [] when it finds none.

    It checks the structure of the document and the gate, verdict and file-accounting facts that it states. It
    cannot check that the review read what the document says, or that its evidence and judgments are right.
    """
    errors = []
    if not _keys(errors, "the document", doc, TOP_KEYS):
        return errors
    if doc["schema"] != SCHEMA:
        return [f'schema must be "{SCHEMA}"']
    if not _is_int(doc["version"]) or doc["version"] != VERSION:
        return [f"version must be {VERSION}; this gate reads only version {VERSION}"]
    status = doc["status"]
    if status not in STATUSES:
        return [f"status must be one of {', '.join(STATUSES)}"]
    message, review = doc["message"], doc["review"]
    if status == "complete":
        if message is not None:
            errors.append("message must be null when status is complete")
        if not _is_text(doc["scope"]):
            errors.append("scope must name the scope of a complete review")
    elif status == "error" and not (isinstance(message, str) and message.startswith("Cannot review: ")
                                    and message.endswith(" Nothing was reviewed.")):
        errors.append("message must be the Cannot review line when status is error")
    elif status == "nothing_to_review" and not (isinstance(message, str) and message.startswith("Nothing to review: ")):
        errors.append("message must be the Nothing to review line when status is nothing_to_review")
    if doc["scope"] is not None and not _is_text(doc["scope"]):
        errors.append("scope must be null or a non-empty string")
    gate = doc["gate"]
    if _keys(errors, "gate", gate, GATE_KEYS):
        if gate["fail_on"] not in ("critical", None):
            errors.append('gate.fail_on must be "critical" or null')
        if gate["status"] not in GATE_STATUSES:
            errors.append(f"gate.status must be one of {', '.join(GATE_STATUSES)}")
        if not _is_text(gate["reason"]):
            errors.append("gate.reason must be a non-empty string")
    if status != "complete":
        if review is not None:
            errors.append(f"review must be null when status is {status}")
    elif _keys(errors, "review", review, REVIEW_KEYS):
        _text_list(errors, "review.context_lines", review["context_lines"])
        _text_list(errors, "review.intent", review["intent"])
        if not (isinstance(review["intent"], list) and review["intent"]
                and str(review["intent"][0]).startswith("**Intent:** ")):
            errors.append("review.intent must start with the **Intent:** line")
        for key, confidence in (("findings", "High"), ("needs_verification", "Medium")):
            if not isinstance(review[key], list):
                errors.append(f"review.{key} must be a list")
                continue
            for i, finding in enumerate(review[key]):
                _finding_errors(errors, f"review.{key}[{i}]", finding, confidence)
        _text_list(errors, "review.pre_existing", review["pre_existing"])
        _text_list(errors, "review.already_raised", review["already_raised"])
        omitted = review["omitted_by_configuration"]
        if omitted is not None and not _is_text(omitted):
            errors.append("review.omitted_by_configuration must be null or the text of that line")
        if _keys(errors, "review.triage", review["triage"], TRIAGE_KEYS):
            for key in TRIAGE_KEYS:
                if not _is_text(review["triage"][key]):
                    errors.append(f"review.triage.{key} must be a non-empty string")
        verdict = review["verdict"]
        if _keys(errors, "review.verdict", verdict, ("ready_to_merge", "row")) and not (
                _is_int(verdict["row"]) and verdict["row"] in ROW_VALUES
                and verdict["ready_to_merge"] == ROW_VALUES[verdict["row"]]):
            errors.append("review.verdict: row must be 1 to 7 and ready_to_merge the value of that row")
        _audit_errors(errors, review["audit"])
        verification = review["verification"]
        if _keys(errors, "review.verification", verification, ("checked", "refuted")) and not (
                _is_int(verification["checked"]) and _is_int(verification["refuted"])
                and 0 <= verification["refuted"] <= verification["checked"]):
            errors.append("review.verification: checked and refuted must be whole numbers, refuted <= checked")
        if errors:
            return errors
        _accounting_errors(errors, review)
        findings = review["findings"] + review["needs_verification"]
        if omitted is None and any(f["omitted_by"] for f in findings):
            errors.append("review.omitted_by_configuration is null, but a finding is omitted by a filter")
        unrefuted = verification["checked"] - verification["refuted"]
        blocking = sum(1 for f in findings if f["severity"] in ("Critical", "Warning"))
        if unrefuted < blocking:
            errors.append(f"review.verification leaves {unrefuted} unrefuted candidates, but {blocking} Critical "
                          "or Warning findings are reported")
        if not review["triage"]["ready_to_merge"].startswith(f"{verdict['ready_to_merge']} — "):
            errors.append(f"review.triage.ready_to_merge must start with \"{verdict['ready_to_merge']} — \"")
        row = expected_row(review)
        if verdict["row"] != row:
            errors.append(f"review.verdict row {verdict['row']} does not match the facts (row {row})")
    if errors:
        return errors
    gate_status = expected_gate(doc)
    if gate["status"] != gate_status:
        errors.append(f'gate status "{gate["status"]}" does not match the facts ("{gate_status}")')
    return errors


def main(argv: list | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("usage: review_gate.py [FILE|-]", file=sys.stderr)
        return INVALID
    try:
        if not args or args[0] == "-":
            data = sys.stdin.buffer.read()
        else:
            with open(args[0], "rb") as f:
                data = f.read()
    except OSError as exc:
        print(f"review-gate: invalid: cannot read {args[0]}: {exc.strerror}")
        return INVALID
    try:
        doc = load(data)
    except GateInputError as exc:
        print(f"review-gate: invalid: {exc}")
        return INVALID
    errors = contract_errors(doc)
    if errors:
        print(f"review-gate: invalid: {errors[0]}")
        for error in errors[1:]:
            print(f"  {error}")
        return INVALID
    if doc["status"] == "error":
        print(f"review-gate: error: {doc['message']}")
        return EXIT["error"]
    if doc["gate"]["fail_on"] != "critical":
        print("review-gate: invalid: the review was not run with --fail-on critical")
        return INVALID
    status = doc["gate"]["status"]
    print(f"review-gate: {status}: {doc['gate']['reason']}")
    return EXIT[status]


if __name__ == "__main__":
    sys.exit(main())
