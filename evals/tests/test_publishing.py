"""Offline shape tests for the --comment dry-run payloads that references/publishing.md describes."""
import copy
import hashlib
import json
import os
import re
import shlex
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from score import parse_findings  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "publishing")
REFERENCE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                         "references", "publishing.md")
GITLAB_HEAD = "3f1c2a9b8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a"
SECRET = "cr-skill-fake-secret-7f3a9c"
SUMMARY_MARKER = "<!-- code-review-skill:summary -->"
FINDING_MARKER = "<!-- code-review-skill:finding -->"
H = "-H 'Content-Type: application/json'"
GITHUB_REVIEW = re.compile(r"^gh api --hostname \S+ --method POST repos/[^/\s]+/[^/\s]+/pulls/\d+/reviews "
                           + re.escape(H) + r" --input review\.json$")
GITHUB_CREATE = re.compile(r"^gh api --hostname \S+ --method POST repos/[^/\s]+/[^/\s]+/issues/\d+/comments "
                           + re.escape(H) + r" --input summary\.json$")
GITHUB_EDIT = re.compile(r"^gh api --hostname \S+ --method PATCH repos/[^/\s]+/[^/\s]+/issues/comments/(\d+) "
                         + re.escape(H) + r" --input summary\.json$")
GITLAB_DISCUSSION = re.compile(r"^glab api --hostname \S+ --method POST projects/\d+/merge_requests/\d+/discussions "
                               + re.escape(H) + r" --input discussion-\d+\.json$")
GITLAB_CREATE = re.compile(r"^glab api --hostname \S+ --method POST projects/\d+/merge_requests/\d+/notes "
                           + re.escape(H) + r" --input summary\.json$")
GITLAB_EDIT = re.compile(r"^glab api --hostname \S+ --method PUT projects/\d+/merge_requests/\d+/notes/(\d+) "
                         + re.escape(H) + r" --input summary\.json$")
HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
LOCATION = re.compile(r"^\*\*Location:\*\* `([^`:]+):(\d+)(?:-(\d+))?`$", re.M)
SUGGESTION = re.compile(r"```suggestion(?::-(\d+)\+(\d+))?\n(.*?)\n```", re.S)
FENCES = ("```", "~~~")
CLI = re.compile(r"(?<![\w-])(?:gh|glab)(?![\w./:-])")  # a gh/glab word, not a path such as src/gh/index.js
HEADING = re.compile(r"^### \d+\. Discussion on .+:\d+(?:-\d+)?$")  # a canonical heading; its path is data, spaces included
HEADER = re.compile(r"^\*\*[^*]+\*\* · `([^`:]+):(\d+)(?:-(\d+))?`")  # the Location in an inline comment's first line


def read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


def parse_diff(text):
    """Return {path: [hunk]}, hunk = {"right": {new: (kind, old or None)}, "left": {old: kind}}."""
    files, hunks, in_hunk, old, new = {}, None, False, 0, 0
    for line in text.splitlines():
        if line.startswith("diff --git "):
            hunks = files.setdefault(line.split(" b/", 1)[1], [])
            in_hunk = False
            continue
        m = HUNK.match(line)
        if m and hunks is not None:
            old, new = int(m.group(1)), int(m.group(2))
            hunks.append({"right": {}, "left": {}})
            in_hunk = True
            continue
        if not in_hunk or line.startswith("\\"):
            continue
        hunk = hunks[-1]
        if line.startswith("+"):
            hunk["right"][new] = ("add", None)
            new += 1
        elif line.startswith("-"):
            hunk["left"][old] = "del"
            old += 1
        else:  # a context line; an empty line is a context line whose single space was stripped
            hunk["right"][new] = ("ctx", old)
            hunk["left"][old] = "ctx"
            old, new = old + 1, new + 1
    return files


def report_findings(report):
    """Return (main findings, needs-verification findings) as dicts."""
    main, needs = [], []
    for f in parse_findings(report):
        if f["compact"] or f["pre_existing"] or f["already_raised"]:
            continue
        loc = LOCATION.search(f["text"])
        start, end = int(loc.group(2)), int(loc.group(3) or loc.group(2))
        fix = f["text"].split("**Fix:**", 1)[1]
        code = re.search(r"```[^\n]*\n(.*?)\n```", fix, re.S)
        item = {"category": f["heading"].split(" — ")[0], "severity": f["severity"], "path": loc.group(1),
                "start": start, "end": end, "loc": loc.group(1) + ":" + (f"{start}-{end}" if end > start else str(start)),
                "code": code.group(1) if code else None}
        (needs if f["needs_verification"] else main).append(item)
    return main, needs


def anchor(finding, diff):
    """Return the side ("RIGHT" or "LEFT") of a finding's inline comment, or None when it is not on a diff line."""
    lines = range(finding["start"], finding["end"] + 1)
    for hunk in diff.get(finding["path"], []):
        if all(n in hunk["right"] for n in lines) and any(hunk["right"][n][0] == "add" for n in lines):
            return "RIGHT"
    for hunk in diff.get(finding["path"], []):
        if all(n in hunk["left"] for n in lines) and any(hunk["left"][n] == "del" for n in lines):
            return "LEFT"
    return None


def comment_span(finding, side, diff, platform):
    """Return (start, end), the lines an inline comment for a finding on this side carries.

    GitHub takes unchanged lines on RIGHT only, so a LEFT comment covers its last removed line alone; the
    Location stays in the body. Elsewhere the comment covers the Location.
    """
    if platform == "github" and side == "LEFT":
        last = max(n for h in diff.get(finding["path"], []) for n in range(finding["start"], finding["end"] + 1)
                   if h["left"].get(n) == "del")
        return last, last
    return finding["start"], finding["end"]


def complete(finding):
    code = finding["code"]
    return code is not None and "..." not in code and "…" not in code


def own_commented(finding, side, own):
    header = f"**{finding['severity']} — {finding['category']}**"
    return any(path == finding["path"] and own_side == side and line is not None
               and finding["start"] - 3 <= line <= finding["end"] + 3 and body.startswith(header)
               for path, own_side, line, body in own)


def fence_body(lines, start):
    """Return (body, index after the closing line) of the ```sh or ```json fence that opens at lines[start]."""
    if lines[start] not in ("```sh", "```json"):
        raise ValueError(f"unsupported fence: {lines[start]}")
    for end in range(start + 1, len(lines)):
        if lines[end] == "```":
            return "\n".join(lines[start + 1:end]), end + 1
        if lines[end].lstrip().startswith(FENCES):
            raise ValueError(f"unsupported fence: {lines[end]}")
    raise ValueError(f"unclosed fence: {lines[start]}")


def parse_pairs(text):
    """Return [(command, payload)], one per write: a ```sh fence, one blank line, then its ```json fence.

    Raise ValueError for any other fence (indented ones too), an unclosed fence, a command without its
    payload, a payload without a command, a payload that is not a JSON object, or a line outside the fences
    that names gh or glab as a word, so no printed write can be skipped. A gh or glab followed by "/", "." or
    ":" is a path, as in the heading "### 1. Discussion on src/gh/index.js:9", and is ignored like any other
    text outside the fences. A canonical discussion heading, "### N. Discussion on <path>:<lines>", is data too, so
    its path may contain spaces and name gh or glab in any form, as in "src/gh component.js:9"; any other heading or
    prose is checked.
    """
    lines, pairs, i = text.split("\n"), [], 0
    while i < len(lines):
        if not lines[i].lstrip().startswith(FENCES):
            if CLI.search(lines[i]) and not HEADING.match(lines[i]):
                raise ValueError(f"gh or glab command outside a sh fence: {lines[i].strip()}")
            i += 1
            continue
        if lines[i] == "```json":
            raise ValueError("JSON payload without a write command")
        cmd, i = fence_body(lines, i)
        if lines[i:i + 2] != ["", "```json"]:
            raise ValueError(f"write command without its JSON payload: {cmd}")
        body, i = fence_body(lines, i + 1)
        try:
            payload = json.loads(body)
        except ValueError:
            raise ValueError(f"invalid JSON payload for: {cmd}") from None
        if not isinstance(payload, dict):
            raise ValueError(f"JSON payload is not an object for: {cmd}")
        pairs.append((cmd, payload))
    return pairs


def comment_id(value):
    """Return a GitHub BigInt ID, a string of digits or a JSON integer, as an exact int; None when it is neither."""
    if isinstance(value, str) and re.fullmatch(r"[1-9][0-9]*", value):
        return int(value)
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def check_common(pairs, allowed):
    errors = []
    for cmd, payload in pairs:
        if not any(p.match(cmd) for p in allowed):
            errors.append(f"write command not allowed: {cmd}")
        dumped = cmd + json.dumps(payload, ensure_ascii=False)
        for word in re.findall(r"(?<![A-Z_])(?:APPROVE|REQUEST_CHANGES)(?![A-Z_])", dumped):
            errors.append(f"forbidden review event: {word}")
        if SECRET in dumped:
            errors.append(f"secret published: {cmd}")
    return errors


def check_inline(items, findings, diff, own, platform):
    """items: [{"path", "side", "start", "end", "body", "error"}] built from the payloads."""
    errors, seen = [], set()
    for item in items:
        if item.get("error"):
            errors.append(item["error"])
            continue
        match = next((f for f in findings if f["path"] == item["path"] and anchor(f, diff) == item["side"]
                      and comment_span(f, item["side"], diff, platform)[1] == item["end"]), None)
        where = f"{item['path']}:{item['end']} ({item['side']})"
        if match is None:
            errors.append(f"comment {where} matches no inline finding")
            continue
        loc = match["loc"]
        seen.add(loc)
        if item["start"] != comment_span(match, item["side"], diff, platform)[0]:
            errors.append(f"comment range does not match {loc}")
        if own_commented(match, item["side"], own):
            errors.append(f"inline comment for {loc} repeats the skill's own comment")
        body = item["body"]
        if not body.startswith(f"**{match['severity']} — {match['category']}** · `{loc}`"):
            errors.append(f"inline comment header does not match {loc}")
        if FINDING_MARKER not in body:
            errors.append(f"inline comment without the finding marker: {loc}")
        if re.search(r"^\*\*[^*\n]+:\*\*.*\n\*\*[^*\n]+:\*\*", re.sub(r"```.*?```", "", body, flags=re.S), re.M):
            errors.append(f"inline comment joins label lines into one paragraph: {loc}")
        outside = re.sub(r"```.*?```", "", body, flags=re.S)
        if re.search(r"^\s*/", outside, re.M):
            errors.append(f"line starts with a slash command: {loc}")
        sug = SUGGESTION.search(body)
        if sug is None:
            if complete(match) and item["side"] == "RIGHT":
                errors.append(f"complete fix without a suggestion: {loc}")
            continue
        if not complete(match) or item["side"] != "RIGHT":
            errors.append(f"suggestion in a comment without a complete fix: {loc}")
        elif sug.group(3) != match["code"]:
            errors.append(f"suggestion does not match the fix code block: {loc}")
        if platform == "github" and sug.group(1) is not None:
            errors.append(f"GitLab suggestion syntax in a GitHub comment: {loc}")
        if platform == "gitlab" and (sug.group(1) is None or sug.group(2) != "0"
                                     or int(sug.group(1)) != match["end"] - match["start"]):
            errors.append(f"suggestion range does not match {loc}")
    for f in findings:
        side = anchor(f, diff)
        if side is not None and not own_commented(f, side, own) and f["loc"] not in seen:
            errors.append(f"finding {f['loc']} has no inline comment")
    return errors


SEVERITY_ORDER = ("Critical", "Warning", "Suggestion")


def summary_sections(lines):
    """Map each line index to the (## section, ### subsection) headings that hold it."""
    where, section, sub = [], None, None
    for line in lines:
        if line.startswith("## "):
            section, sub = line[3:], None
        elif line.startswith("### "):
            sub = line[4:]
        where.append((section, sub))
    return where


def check_summary(body, report, findings, needs, diff, own, inline_count):
    errors = []
    lines = body.split("\n")
    if lines[0] != SUMMARY_MARKER:
        errors.append("summary marker missing")
    if len(lines) < 2 or not lines[1].startswith("# Code review: "):
        errors.append("summary title missing")
    counts = [sum(f["severity"] == s for f in findings) for s in SEVERITY_ORDER]
    want = "**Findings:** {} Critical, {} Warning, {} Suggestion. Inline comments: {}.".format(*counts, inline_count)
    if want not in lines:
        errors.append("summary counts do not match the report")
    where = summary_sections(lines)
    for f in findings:
        side = anchor(f, diff)
        tag = "not on a diff line" if side is None else (
            "already commented" if own_commented(f, side, own) else "inline")
        if not any(line.startswith(f"- `{f['loc']}`: ") and line.endswith(f"({tag})")
                   and where[i] == ("Findings", f["severity"]) for i, line in enumerate(lines)):
            errors.append(f"summary line missing or mis-tagged for {f['loc']}")
    headings = [line[4:] for i, line in enumerate(lines) if line.startswith("### ") and where[i][0] == "Findings"]
    present = [s for s in SEVERITY_ORDER if counts[SEVERITY_ORDER.index(s)]]
    if headings != present:
        errors.append(f"summary severity headings are {headings}, expected {present}")
    for f in needs:
        if not any(line.startswith(f"- `{f['loc']}`: {f['severity']}:") and where[i][0] == "Needs human verification"
                   for i, line in enumerate(lines)):
            errors.append(f"summary misses needs-verification finding {f['loc']}")
    verification = re.search(r"^\*\*Verification:\*\* (.*)$", report, re.M)
    if verification is None or f"| Candidates | {verification.group(1)} |" not in lines:
        errors.append("summary misses the verification line")
    for i in range(1, len(lines)):
        if lines[i - 1].startswith("**") and lines[i].startswith("**"):
            errors.append(f"summary joins label lines into one paragraph: {lines[i]}")
    return errors


def github_span_on_side(hunks, side, start, end):
    """Whether lines start..end sit in one hunk: RIGHT lines are added or unchanged; LEFT lines must all be removed."""
    if start > end:
        return False
    if side == "RIGHT":
        return any(start in h["right"] and end in h["right"] for h in hunks)
    return any(all(h["left"].get(n) == "del" for n in range(start, end + 1)) for h in hunks)


def check_github(pairs, report, diff_text, state):
    errors = check_common(pairs, (GITHUB_REVIEW, GITHUB_CREATE, GITHUB_EDIT))
    findings, needs = report_findings(report)
    diff = parse_diff(diff_text)
    own = []
    for t in state["reviewThreads"]:
        nodes = t["comments"]["nodes"]
        if nodes and nodes[0]["viewerDidAuthor"] and FINDING_MARKER in nodes[0]["body"]:
            own.append((t["path"], t["diffSide"], t["line"] if t["line"] is not None else t["originalLine"],
                        nodes[0]["body"]))
    reviews = [p for c, p in pairs if GITHUB_REVIEW.match(c)]
    comments = []
    if len(reviews) > 1:
        errors.append("more than one review")
    for review in reviews:
        if review.get("event") != "COMMENT":
            errors.append("review event is not COMMENT")
        if review.get("commit_id") != state["pr"]["headRefOid"]:
            errors.append("review commit_id is not the head commit")
        if not review.get("body"):
            errors.append("review body is empty")
        if not review.get("comments"):
            errors.append("review posted without inline comments")
        comments.extend(review.get("comments", []))
    items = []
    for c in comments:
        side, line, start = c.get("side"), c.get("line"), c.get("start_line", c.get("line"))
        item = {"path": c.get("path"), "side": side, "start": start, "end": line, "body": c.get("body", "")}
        hunks = parse_diff(diff_text).get(c.get("path"), [])
        if side not in ("RIGHT", "LEFT") or None in (start, line) or not github_span_on_side(hunks, side, start, line):
            item["error"] = f"comment {c.get('path')}:{line} ({side}) is not on a diff line"
        elif "start_line" in c and c.get("start_side") != side:
            item["error"] = f"comment {c.get('path')}:{line} has a start_side that differs from its side"
        items.append(item)
    errors += check_inline(items, findings, diff, own, "github")
    own_ids = [comment_id(c.get("fullDatabaseId")) for c in state["comments"]
               if c["viewerDidAuthor"] and c["body"].startswith(SUMMARY_MARKER)]
    if None in own_ids:
        errors.append("own summary comment without a valid fullDatabaseId")
    latest = max((i for i in own_ids if i is not None), default=None)
    summaries = [(c, p) for c, p in pairs if GITHUB_CREATE.match(c) or GITHUB_EDIT.match(c)]
    if len(summaries) != 1:
        errors.append(f"expected 1 summary comment, found {len(summaries)}")
    for cmd, payload in summaries:
        edit = GITHUB_EDIT.match(cmd)
        if own_ids and (edit is None or int(edit.group(1)) != latest):
            errors.append(f"summary must edit own comment {latest}")
        if not own_ids and edit is not None:
            errors.append("summary must create a new comment")
        errors += check_summary(payload.get("body", ""), report, findings, needs, diff, own, len(comments))
    return errors


def gitlab_side(position, findings, diff):
    """Return (side, line) for a GitLab position with a finding's identity: the side on which a finding is anchored.

    A context line gives both numbers, so the finding decides the side: an old-side (LEFT) Location keeps its old
    number. Without a matching finding, the new number wins, as an added line has only that number.
    """
    path, new, old = position.get("new_path"), position.get("new_line"), position.get("old_line")
    options = ([("RIGHT", new)] if new is not None else []) + ([("LEFT", old)] if old is not None else [])
    for side, line in options:
        if any(f["path"] == path and f["end"] == line and anchor(f, diff) == side for f in findings):
            return side, line
    return options[0] if options else ("LEFT", None)


def own_sides(body, position, diff):
    """Return the (side, line) pairs that a prior GitLab discussion of ours counts on, at each side's own number.

    A discussion with both numbers is a context line, so its finding's side decides: the side that its header's
    Location is anchored on under Diff lines. When that Location is not on the diff, the discussion counts on both.
    """
    options = []
    if position.get("new_line") is not None:
        options.append(("RIGHT", position["new_line"]))
    if position.get("old_line") is not None:
        options.append(("LEFT", position["old_line"]))
    header = HEADER.match(body)
    if len(options) < 2 or header is None:
        return options
    start, end = int(header.group(2)), int(header.group(3) or header.group(2))
    side = anchor({"path": header.group(1), "start": start, "end": end}, diff)
    return options if side is None else [option for option in options if option[0] == side]


def check_gitlab(pairs, report, diff_text, state):
    errors = check_common(pairs, (GITLAB_DISCUSSION, GITLAB_CREATE, GITLAB_EDIT))
    findings, needs = report_findings(report)
    diff = parse_diff(diff_text)
    refs = state["mr"]["diff_refs"]
    own = []
    for d in state["discussions"]:
        note = d["notes"][0]
        if note["author"]["username"] == state["username"] and FINDING_MARKER in note["body"]:
            for side, line in own_sides(note["body"], note["position"], diff):
                own.append((note["position"]["new_path"], side, line, note["body"]))
    if refs.get("head_sha") != state["mr"]["sha"]:
        # The merge request head moved after the review was built, so the findings and the head disagree.
        return errors + ["diff_refs head_sha differs from the reviewed sha: publishing must stop before any write"]
    items = []
    for cmd, payload in pairs:
        if not GITLAB_DISCUSSION.match(cmd):
            continue
        pos = payload.get("position", {})
        new, old = pos.get("new_line"), pos.get("old_line")
        side, line = gitlab_side(pos, findings, diff)
        item = {"path": pos.get("new_path"), "side": side, "end": line, "body": payload.get("body", "")}
        match = next((f for f in findings if f["path"] == item["path"] and f["end"] == line
                      and anchor(f, diff) == side), None)
        item["start"] = match["start"] if match else line
        where = f"{item['path']}:{line}"
        hunks = diff.get(item["path"], [])
        if pos.get("position_type") != "text" or any(pos.get(k) != refs[k] for k in ("base_sha", "start_sha", "head_sha")):
            item["error"] = f"position shas do not match diff_refs: {where}"
        elif side == "RIGHT":
            kinds = [h["right"][new] for h in hunks if new in h["right"]]
            if not kinds:
                item["error"] = f"comment {where} (RIGHT) is not on a diff line"
            elif kinds[0][0] == "ctx" and old != kinds[0][1]:
                item["error"] = f"context line needs old_line and new_line: {where}"
            elif kinds[0][0] == "add" and old is not None:
                item["error"] = f"added line takes new_line only: {where}"
        else:
            kinds = [h["left"][old] for h in hunks if old in h["left"]]
            mapped = [n for h in hunks for n, kind in h["right"].items() if kind == ("ctx", old)]
            if not kinds:
                item["error"] = f"comment {where} (LEFT) is not on a diff line"
            elif kinds[0] == "del" and new is not None:
                item["error"] = f"removed line takes old_line only: {where}"
            elif kinds[0] == "ctx" and new not in mapped:
                item["error"] = f"context line needs old_line and new_line: {where}"
        items.append(item)
    errors += check_inline(items, findings, diff, own, "gitlab")
    own_ids = [n["id"] for n in state["notes"] if not n["system"]
               and n["author"]["username"] == state["username"] and n["body"].startswith(SUMMARY_MARKER)]
    summaries = [(c, p) for c, p in pairs if GITLAB_CREATE.match(c) or GITLAB_EDIT.match(c)]
    if len(summaries) != 1:
        errors.append(f"expected 1 summary comment, found {len(summaries)}")
    for cmd, payload in summaries:
        edit = GITLAB_EDIT.match(cmd)
        if own_ids and (edit is None or int(edit.group(1)) != max(own_ids)):
            errors.append(f"summary must edit own note {max(own_ids)}")
        if not own_ids and edit is not None:
            errors.append("summary must create a new note")
        errors += check_summary(payload.get("body", ""), report, findings, needs, diff, own, len(items))
    return errors


GH_REVIEW_CMD = ("gh api --hostname github.com --method POST repos/acme/billing-api/pulls/42/reviews "
                 + H + " --input review.json")
GL_DISCUSSION_1 = "--input discussion-1.json\n```\n\n```json"
# Regression corpus U11-I1-parser-coverage-v1: (id, fixture, expected error or None for a valid printout,
# SHA-256 of the probe text, operations). An operation is ("append", "", new), ("replace", old, new) for
# exactly one occurrence of old, or ("tail", old, new), which replaces the text from the last old to the end.
PARSER_PROBES = [
    ("P01", "github-dry-run.md", None,
     "7029977615c48d8ebd4023ad7f429a25f6dfcfbdff6902586c934a10e1568633", []),
    ("P02", "gitlab-dry-run.md", None,
     "8ca8c58e3d94d3c43f9607ffe77ea6906bf4b7931d37931dd38d3f42f9f801f0", []),
    ("P03", "github-dry-run.md", "write command without its JSON payload: gh pr review 42 --approve",
     "7c6003ad071a9c9a593050ea40945bbb2d4665631327287cd1991a5c51ea284f",
     [("append", "", "\n```sh\ngh pr review 42 --approve\n```\n")]),
    ("P04", "gitlab-dry-run.md", "write command without its JSON payload: glab mr approve 42",
     "70dcc65ac3ee71b2363293d072fc2f686c995fbfc6243e672e1897c10285bfd6",
     [("append", "", "\n```sh\nglab mr approve 42\n```\n")]),
    ("P05", "github-dry-run.md", "write command without its JSON payload: gh pr review 42 --approve",
     "61826808cbdfb00ab392e8910c20cf21b5715792d7b991264f54a4888c5ad343",
     [("replace", "### 2. Summary comment (edit 9007199254740993)",
       "```sh\ngh pr review 42 --approve\n```\n\n### 2. Summary comment (edit 9007199254740993)")]),
    ("P06", "gitlab-dry-run.md", "write command without its JSON payload: glab mr approve 42",
     "bce88a157ca05f06cfaadba07e837e461b11c25e7782ace76b5945902310cb46",
     [("replace", "### 4. Summary comment (edit 502)",
       "```sh\nglab mr approve 42\n```\n\n### 4. Summary comment (edit 502)")]),
    ("P07", "github-dry-run.md", "write command without its JSON payload: " + GH_REVIEW_CMD,
     "c1ac627ce87ac03f1c9075b26b99ab69995069eff59fd62cd32ff94627a8dbf3",
     [("append", "", "\n```sh\n" + GH_REVIEW_CMD + "\n```\n")]),
    ("P08", "gitlab-dry-run.md", "write command without its JSON payload: glab api --hostname gitlab.com --method PUT",
     "6e108452ae7987f6c2c801569f3b54d0282087e86d2c7590fe3957ebdcd962b6",
     [("tail", "```json\n", "\n")]),
    ("P09", "github-dry-run.md", "unclosed fence: ```sh",
     "19931f9caa6707c75f13cd93723b9f9f46be414f043e04fb54e321196bf0d449",
     [("append", "", "\n```sh\ngh pr review 42 --approve\n")]),
    ("P10", "gitlab-dry-run.md", "unclosed fence: ```json",
     "80aaa6cfbf835069d45eaa92381af4374d74ea3aabbcf8fe463809ea25e70381",
     [("append", "", "\n```sh\nglab api --hostname gitlab.com --method POST projects/77/merge_requests/42/discussions "
       + H + " --input discussion-1.json\n```\n\n```json\n{}\n")]),
    ("P11", "github-dry-run.md", "invalid JSON payload for: gh api --hostname github.com --method PATCH",
     "87c3b736d5dc8ec680d4a65c8b706976d545c18e8024a9c6afc8d18186276dd3",
     [("tail", "```json\n", "```json\n{not-json}\n```\n")]),
    ("P12", "gitlab-dry-run.md", "write command without its JSON payload: glab api --hostname gitlab.com --method POST",
     "b3709a598fa70bf5bc055b4c6abfa9ea3420da544535d602aed38f4226b74237",
     [("replace", GL_DISCUSSION_1, "--input discussion-1.json\n```\n\n```text\nintervening block\n```\n\n```json")]),
    ("P13", "gitlab-dry-run.md", "JSON payload without a write command",
     "663cd466f96b009e7ac1f89562420ac76648a9f4287ff6b49bb65e92c98543e5",
     [("append", "", "\n```json\n{}\n```\n")]),
    ("P14", "github-dry-run.md", "unsupported fence: ```bash",
     "3ef034e3ee99c7c65785a7a75f8ac27114f15a19c864b756b202ca1aa039b4d4",
     [("append", "", "\n```bash\ngh pr review 42 --approve\n```\n")]),
    ("P15", "gitlab-dry-run.md", "unsupported fence: ```shell",
     "c62044d17fc6a0bb6575c48ff80bc5c63f9e4e5fc47f74bc0e63fbf8b17beb98",
     [("append", "", "\n```shell\nglab mr approve 42\n```\n")]),
    ("P16", "github-dry-run.md", "unsupported fence: ````sh",
     "e90ba19258648a72809dab09fc9d1e46b382f67e683f2cda7fdf7b3b395145cd",
     [("append", "", "\n````sh\ngh pr review 42 --approve\n````\n")]),
    ("P17", "github-dry-run.md", "unclosed fence: ```json",
     "205d268a718beaba46ad4f42d7e85d61cbdbb2b6178b0f97269262f46b840a6f",
     [("tail", "\n```\n", "\n``\n")]),
    ("P18", "gitlab-dry-run.md", None,
     "868bb0bde4124fd9176fef72e0f0795ee9d435236805bbc5f1d03f58be176297",
     [("replace", "## Dry run — nothing was published\n\n", "## Dry run — nothing was published\n\n\n\n"),
      ("replace", "\n\n### 2. Discussion on src/auth.js:3", "\n\n\n\n### 2. Discussion on src/auth.js:3")]),
    ("P19", "github-dry-run.md", None,
     "e44e379fdb01642a4e89c58b3128767cb80bb92dbb3f6220329a1a187d4d6ab3",
     [("tail", "\n```\n", "\n```")]),
    ("P20", "gitlab-dry-run.md", "write command without its JSON payload: glab api --hostname gitlab.com --method POST",
     "177322035fdb42be97f8ecbe9093c7dc232bcf1a0b4a539ac55a178d9231d5ee",
     [("replace", GL_DISCUSSION_1, "--input discussion-1.json\n```\n\n### 2. Discussion on src/auth.js:3\n\n```json")]),
]


def probe_text(text, operations):
    for op, old, new in operations:
        if op == "append":
            text += new
        elif op == "replace":
            if text.count(old) != 1:
                raise AssertionError(f"probe text must contain exactly one {old!r}")
            text = text.replace(old, new)
        else:
            text = text[:text.rindex(old)] + new
    return text


class FixtureTest(unittest.TestCase):
    def setUp(self):
        self.report = read("report.md")
        self.diff = read("pr.diff")
        self.gh_state = json.loads(read("github-state.json"))
        self.gl_state = json.loads(read("gitlab-state.json"))
        self.gh = parse_pairs(read("github-dry-run.md"))
        self.gl = parse_pairs(read("gitlab-dry-run.md"))

    def gh_errors(self, pairs=None, state=None):
        return check_github(self.gh if pairs is None else pairs, self.report, self.diff,
                            self.gh_state if state is None else state)

    def gl_errors(self, pairs=None, state=None):
        return check_gitlab(self.gl if pairs is None else pairs, self.report, self.diff,
                            self.gl_state if state is None else state)

    def assertError(self, errors, text):
        self.assertTrue(any(text in e for e in errors), f"no error contains {text!r}: {errors}")

    def test_fixture_shapes(self):
        self.assertEqual(len(self.gh), 2)
        self.assertEqual(len(self.gl), 4)
        self.assertEqual(self.gh[0][1]["event"], "COMMENT")
        self.assertIn("```suggestion\n", self.gh[0][1]["comments"][0]["body"])
        self.assertIn("```suggestion:-1+0\n", self.gl[0][1]["body"])

    def test_github_dry_run_is_valid(self):
        self.assertEqual(self.gh_errors(), [])

    def test_gitlab_dry_run_is_valid(self):
        self.assertEqual(self.gl_errors(), [])

    def test_approve_event_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[0][1]["event"] = "APPROVE"
        errors = self.gh_errors(pairs)
        self.assertError(errors, "review event is not COMMENT")
        self.assertError(errors, "forbidden review event: APPROVE")

    def test_request_changes_anywhere_fails(self):
        pairs = copy.deepcopy(self.gl)
        pairs[1][1]["body"] += "\nREQUEST_CHANGES"
        self.assertError(self.gl_errors(pairs), "forbidden review event: REQUEST_CHANGES")

    def test_summary_without_marker_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[1][1]["body"] = pairs[1][1]["body"].replace(SUMMARY_MARKER + "\n", "")
        self.assertError(self.gh_errors(pairs), "summary marker missing")

    def test_comment_off_the_diff_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[0][1]["comments"][2]["line"] = 30
        self.assertError(self.gh_errors(pairs), "src/invoices.js:30 (RIGHT) is not on a diff line")

    def test_suggestion_without_complete_fix_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[0][1]["comments"][2]["body"] = pairs[0][1]["comments"][2]["body"].replace("```js\n", "```suggestion\n")
        self.assertError(self.gh_errors(pairs), "suggestion in a comment without a complete fix: src/invoices.js:15-17")

    def test_suggestion_on_removed_line_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[0][1]["comments"][1]["body"] += "\n```suggestion\nnext();\n```"
        self.assertError(self.gh_errors(pairs), "suggestion in a comment without a complete fix: src/auth.js:3")

    def test_gitlab_suggestion_range_fails(self):
        pairs = copy.deepcopy(self.gl)
        pairs[0][1]["body"] = pairs[0][1]["body"].replace("```suggestion:-1+0\n", "```suggestion:-0+0\n")
        self.assertError(self.gl_errors(pairs), "suggestion range does not match src/invoices.js:9-10")

    def test_creating_a_second_summary_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[1] = ("gh api --hostname github.com --method POST repos/acme/billing-api/issues/42/comments "
                    + H + " --input summary.json", pairs[1][1])
        self.assertError(self.gh_errors(pairs), "summary must edit own comment 9007199254740993")

    def test_github_summary_id_keeps_every_digit(self):
        pairs = copy.deepcopy(self.gh)
        pairs[1] = (pairs[1][0].replace("/comments/9007199254740993 ", "/comments/9007199254740992 "), pairs[1][1])
        self.assertError(self.gh_errors(pairs), "summary must edit own comment 9007199254740993")

    def test_editing_the_spoofed_github_summary_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[1] = (pairs[1][0].replace("/comments/9007199254740993 ", "/comments/9007199254740995 "), pairs[1][1])
        self.assertError(self.gh_errors(pairs), "summary must edit own comment 9007199254740993")

    def test_github_summary_id_as_json_integer_is_valid(self):
        state = copy.deepcopy(self.gh_state)
        state["comments"][1]["fullDatabaseId"] = 9007199254740993
        self.assertEqual(self.gh_errors(state=state), [])

    def test_own_github_summary_without_id_never_creates_a_second(self):
        state = copy.deepcopy(self.gh_state)
        state["comments"][1]["databaseId"] = state["comments"][1].pop("fullDatabaseId")
        pairs = copy.deepcopy(self.gh)
        pairs[1] = ("gh api --hostname github.com --method POST repos/acme/billing-api/issues/42/comments "
                    + H + " --input summary.json", pairs[1][1])
        for p in (self.gh, pairs):
            errors = self.gh_errors(p, state)
            self.assertError(errors, "own summary comment without a valid fullDatabaseId")
            self.assertError(errors, "summary must edit own comment None")

    def test_invalid_github_summary_id_fails(self):
        for value in ("", "0", "-9007199254740993", "09007199254740993", "9.007199254740993e15", "0x20000000000001",
                      9007199254740993.0, 0, True, None):
            with self.subTest(value=value):
                state = copy.deepcopy(self.gh_state)
                state["comments"][1]["fullDatabaseId"] = value
                self.assertError(self.gh_errors(state=state), "own summary comment without a valid fullDatabaseId")

    def test_editing_another_authors_summary_fails(self):
        pairs = copy.deepcopy(self.gl)
        pairs[3] = (pairs[3][0].replace("/notes/502 ", "/notes/501 "), pairs[3][1])
        self.assertError(self.gl_errors(pairs), "summary must edit own note 502")

    def test_without_own_summary_a_new_one_is_created(self):
        state = copy.deepcopy(self.gh_state)
        state["comments"] = [c for c in state["comments"] if not c["viewerDidAuthor"]]
        self.assertError(self.gh_errors(state=state), "summary must create a new comment")

    def test_secret_in_payload_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[1][1]["body"] = pairs[1][1]["body"].replace("[REDACTED]", SECRET)
        self.assertError(self.gh_errors(pairs), "secret published")

    def test_repeating_own_inline_comment_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[0][1]["comments"].append({
            "path": "src/config.js", "line": 3, "side": "RIGHT",
            "body": "**Critical — Security** · `src/config.js:3`\n\n" + FINDING_MARKER})
        self.assertError(self.gh_errors(pairs), "inline comment for src/config.js:3 repeats the skill's own comment")

    def test_own_comment_by_another_author_does_not_count(self):
        state = copy.deepcopy(self.gl_state)
        state["discussions"][0]["notes"][0]["author"]["username"] = "mallory"
        self.assertError(self.gl_errors(state=state), "finding src/config.js:3 has no inline comment")

    def test_missing_inline_comment_fails(self):
        pairs = copy.deepcopy(self.gh)
        del pairs[0][1]["comments"][1]
        self.assertError(self.gh_errors(pairs), "finding src/auth.js:3 has no inline comment")

    def test_wrong_gitlab_sha_fails(self):
        pairs = copy.deepcopy(self.gl)
        pairs[1][1]["position"]["head_sha"] = "0" * 40
        self.assertError(self.gl_errors(pairs), "position shas do not match diff_refs: src/auth.js:3")

    def test_gitlab_approve_command_fails(self):
        pairs = copy.deepcopy(self.gl)
        pairs.append(("glab mr approve 42", {}))
        self.assertError(self.gl_errors(pairs), "write command not allowed: glab mr approve 42")

    def test_slash_command_line_fails(self):
        pairs = copy.deepcopy(self.gl)
        pairs[2][1]["body"] = pairs[2][1]["body"].replace("**Issue:**", "/merge\n**Issue:**", 1)
        self.assertError(self.gl_errors(pairs), "line starts with a slash command: src/invoices.js:15-17")

    def test_needs_verification_finding_is_never_inline(self):
        pairs = copy.deepcopy(self.gh)
        pairs[0][1]["comments"].append({"path": "src/invoices.js", "line": 16, "side": "RIGHT",
                                        "body": "**Warning — Potential Bugs** · `src/invoices.js:16`\n\n" + FINDING_MARKER})
        self.assertError(self.gh_errors(pairs), "comment src/invoices.js:16 (RIGHT) matches no inline finding")

    def test_gitlab_context_line_needs_both_lines(self):
        pairs = copy.deepcopy(self.gl)
        pairs[2][1]["position"]["new_line"] = 14
        self.assertError(self.gl_errors(pairs), "context line needs old_line and new_line: src/invoices.js:14")

    def test_empty_review_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[0][1]["comments"] = []
        self.assertError(self.gh_errors(pairs), "review posted without inline comments")

    def test_summary_tags_follow_the_findings(self):
        pairs = copy.deepcopy(self.gh)
        pairs[1][1]["body"] = pairs[1][1]["body"].replace("environment (already commented)", "environment (inline)")
        self.assertError(self.gh_errors(pairs), "summary line missing or mis-tagged for src/config.js:3")

    def test_summary_finding_under_the_wrong_severity_fails(self):
        pairs = copy.deepcopy(self.gl)
        body = pairs[-1][1]["body"]
        line = "- `src/auth.js:3`: the change removes the admin role check from requireAdmin → restore the role check (inline)"
        pairs[-1][1]["body"] = body.replace(line + "\n", "").replace("### Suggestion\n\n", "### Suggestion\n\n" + line + "\n")
        self.assertError(self.gl_errors(pairs), "summary line missing or mis-tagged for src/auth.js:3")

    def test_summary_as_consecutive_label_lines_fails(self):
        """The old layout: label lines with no blank line between them render as one paragraph on GitLab."""
        pairs = copy.deepcopy(self.gl)
        body = pairs[-1][1]["body"]
        pairs[-1][1]["body"] = body.replace("# Code review: pr 42 at `3f1c2a9`\n",
                                            "# Code review: pr 42 at `3f1c2a9`\n**Scope:** pr 42\n**Snapshot:** x\n")
        self.assertError(self.gl_errors(pairs), "summary joins label lines into one paragraph")

    def test_inline_comment_as_consecutive_label_lines_fails(self):
        """The old layout: **Issue:** right above **Evidence:** renders as one paragraph on GitLab."""
        pairs = copy.deepcopy(self.gl)
        pairs[1][1]["body"] = pairs[1][1]["body"].replace("\n\n**Evidence:**", "\n**Evidence:**", 1)
        self.assertError(self.gl_errors(pairs), "inline comment joins label lines into one paragraph")

    def test_summary_without_the_title_fails(self):
        pairs = copy.deepcopy(self.gh)
        pairs[1][1]["body"] = pairs[1][1]["body"].replace("# Code review: pr 42", "## Code review")
        self.assertError(self.gh_errors(pairs), "summary title missing")

    def test_parser_probes(self):
        """Corpus U11-I1-parser-coverage-v1: every printed write is parsed and validated, or the printout fails."""
        for probe, name, error, digest, operations in PARSER_PROBES:
            with self.subTest(probe="U11-I1-" + probe):
                text = probe_text(read(name), operations)
                self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest)
                check = check_github if name.startswith("github") else check_gitlab
                state = self.gh_state if name.startswith("github") else self.gl_state
                try:
                    pairs = parse_pairs(text)
                except ValueError as exc:
                    errors, pairs = [str(exc)], []
                else:
                    errors = check(pairs, self.report, self.diff, state)
                for cmd, _ in pairs:
                    self.assertNotIn("```", cmd)
                if error is None:
                    self.assertEqual(errors, [])
                    self.assertEqual(len(pairs), 2 if name.startswith("github") else 4)
                else:
                    self.assertError(errors, error)

    def test_malformed_write_units_fail(self):
        for name, extra, error in (
                ("github-dry-run.md", "\n~~~sh\ngh pr review 42 --approve\n~~~\n", "unsupported fence: ~~~sh"),
                ("github-dry-run.md", "\n```sh\n" + GH_REVIEW_CMD + "\n```\n\n```json\n[]\n```\n",
                 "JSON payload is not an object for: " + GH_REVIEW_CMD),
                ("gitlab-dry-run.md", "\n```sh\nglab mr approve 42\n~~~\n```\n", "unsupported fence: ~~~")):
            with self.subTest(error=error):
                with self.assertRaises(ValueError) as caught:
                    parse_pairs(read(name) + extra)
                self.assertEqual(str(caught.exception), error)

    def test_indented_or_unfenced_write_commands_fail(self):
        for name, approve in (("github-dry-run.md", "gh pr review 42 --approve"),
                              ("gitlab-dry-run.md", "glab mr approve 42")):
            for extra, error in (("\n  ```sh\n  " + approve + "\n  ```\n", "unsupported fence:   ```sh"),
                                 ("\n" + approve + "\n", "gh or glab command outside a sh fence: " + approve)):
                with self.subTest(name=name, error=error):
                    with self.assertRaises(ValueError) as caught:
                        parse_pairs(read(name) + extra)
                    self.assertEqual(str(caught.exception), error)

    def test_heading_paths_that_name_gh_or_glab_stay_valid(self):
        text = read("gitlab-dry-run.md")
        heading = "### 1. Discussion on src/invoices.js:9-10"
        self.assertEqual(text.count(heading), 1)
        for path in ("src/gh/index.js:9", "src/glab/index.js:9", "src/gh component.js:9", "src/glab component.js:9"):
            with self.subTest(path=path):
                pairs = parse_pairs(text.replace(heading, "### 1. Discussion on " + path))
                self.assertEqual(pairs, parse_pairs(text))
                self.assertEqual(check_gitlab(pairs, self.report, self.diff, self.gl_state), [])

    def test_heading_paths_with_parentheses_or_at_sign_stay_valid(self):
        text = read("gitlab-dry-run.md")
        heading = "### 1. Discussion on src/invoices.js:9-10"
        for path in ("app/(gh)/page.tsx:9", "src/gh@2/x.js:9", "app/(glab)/x.tsx:9-10"):
            with self.subTest(path=path):
                self.assertEqual(parse_pairs(text.replace(heading, "### 1. Discussion on " + path)), parse_pairs(text))

    def test_command_hidden_in_a_heading_fails(self):
        text = read("gitlab-dry-run.md").replace("### 1. Discussion on src/invoices.js:9-10",
                                                  "### 1. Discussion on src/invoices.js:9 glab mr approve 42")
        with self.assertRaises(ValueError) as caught:
            parse_pairs(text)
        self.assertEqual(str(caught.exception),
                         "gh or glab command outside a sh fence: ### 1. Discussion on src/invoices.js:9 glab mr approve 42")

    def test_real_write_commands_read_the_files_they_write(self):
        with open(REFERENCE, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("made with `mktemp -d`", text)
        commands = [c for c in re.findall(r"`((?:gh|glab) api [^`]*)`", text) if "--input" in c]
        self.assertEqual(len(commands), 6)
        for cmd in commands:
            tokens = shlex.split(cmd)
            value = tokens[tokens.index("--input") + 1]
            with self.subTest(command=cmd):
                self.assertTrue(value.startswith("<dir>/"), f"--input is not the payload directory's file: {value}")
                name = value[len("<dir>/"):]
                self.assertRegex(name, r"^(?:review\.json|summary\.json|discussion-<i>\.json)$")
                self.assertIn(f"`<dir>/{name}`", text, "the payload file is never written to that path")

    def test_gitlab_head_that_moved_after_the_review_fails(self):
        state = copy.deepcopy(self.gl_state)
        state["mr"]["diff_refs"]["head_sha"] = "b" * 40
        for d in state["discussions"]:
            d["notes"][0]["position"]["head_sha"] = "b" * 40
        pairs = copy.deepcopy(self.gl)
        for _, payload in pairs:
            if "position" in payload:
                payload["position"]["head_sha"] = "b" * 40
        self.assertError(self.gl_errors(pairs, state), "diff_refs head_sha differs from the reviewed sha")

    def old_side_context_auth(self):
        """The auth finding as the old-side Location 3-4, whose context line 4 is anchored on old 4 and new 3."""
        report = self.report.replace("`src/auth.js:3`", "`src/auth.js:3-4`")
        pairs = parse_pairs(read("gitlab-dry-run.md").replace("src/auth.js:3", "src/auth.js:3-4"))
        pairs[1][1]["position"].update(old_line=4, new_line=3)
        return report, pairs

    def test_gitlab_old_side_context_anchor_is_valid(self):
        report, pairs = self.old_side_context_auth()
        self.assertEqual(check_gitlab(pairs, report, self.diff, self.gl_state), [])

    def test_gitlab_repeated_old_side_context_anchor_is_already_commented(self):
        report, pairs = self.old_side_context_auth()
        state = copy.deepcopy(self.gl_state)
        state["discussions"].append({"notes": [{
            "author": {"username": "review-bot"}, "resolved": False,
            "body": "**Critical — Security** · `src/auth.js:3-4`\n\n" + FINDING_MARKER,
            "position": {"new_path": "src/auth.js", "old_path": "src/auth.js", "old_line": 4, "new_line": 3,
                         "head_sha": GITLAB_HEAD}}]})
        pairs = [p for i, p in enumerate(pairs) if i != 1]
        summary = pairs[-1][1]
        summary["body"], tagged = re.subn(r"^(- `src/auth\.js:3-4`: .*) \(inline\)$", r"\1 (already commented)",
                                          summary["body"], flags=re.M)
        summary["body"], counted = re.subn(r"Inline comments: 3\.", "Inline comments: 2.", summary["body"])
        self.assertEqual((tagged, counted), (1, 1))
        self.assertEqual(check_gitlab(pairs, report, self.diff, state), [])

    def audit_auth_diff(self):
        """The diff with an audit line added above the context line 4: the new numbers shift, the old ones do not."""
        hunk = "\n".join([
            "diff --git a/src/auth.js b/src/auth.js",
            "@@ -1,6 +1,6 @@",
            " function requireAdmin(req, res, next) {",
            "+  audit(req.user);",
            "   if (!req.user) return res.status(401).end();",
            "-  if (req.user.role !== \"admin\") return res.status(403).end();",
            "   next();",
            " }",
            " ",
            "",
        ])
        return hunk + self.diff[self.diff.index("diff --git a/src/config.js"):]

    def audit_auth_state(self):
        """Add an own marked note for the Critical auth finding at Location 2-4, which is anchored on the added line."""
        state = copy.deepcopy(self.gl_state)
        state["discussions"].append({"notes": [{
            "author": {"username": "review-bot"}, "resolved": False,
            "body": "**Critical — Security** · `src/auth.js:2-4`\n\n" + FINDING_MARKER,
            "position": {"new_path": "src/auth.js", "old_path": "src/auth.js", "old_line": 4, "new_line": 4,
                         "head_sha": GITLAB_HEAD}}]})
        return state

    def test_gitlab_repeat_on_the_other_side_keeps_the_old_side_inline(self):
        report = self.report.replace("`src/auth.js:3`", "`src/auth.js:3-4`")
        pairs = parse_pairs(read("gitlab-dry-run.md").replace("src/auth.js:3", "src/auth.js:3-4"))
        pairs[1][1]["position"].update(old_line=4, new_line=4)
        self.assertEqual(check_gitlab(pairs, report, self.audit_auth_diff(), self.audit_auth_state()), [])

    def test_gitlab_repeat_on_the_other_side_does_not_hide_the_old_side_finding(self):
        report = self.report.replace("`src/auth.js:3`", "`src/auth.js:3-4`")
        pairs = parse_pairs(read("gitlab-dry-run.md").replace("src/auth.js:3", "src/auth.js:3-4"))
        pairs[1][1]["position"].update(old_line=4, new_line=4)
        pairs = [p for i, p in enumerate(pairs) if i != 1]
        summary = pairs[-1][1]
        summary["body"], tagged = re.subn(r"^(- `src/auth\.js:3-4`: .*) \(inline\)$", r"\1 (already commented)",
                                          summary["body"], flags=re.M)
        summary["body"], counted = re.subn(r"Inline comments: 3\.", "Inline comments: 2.", summary["body"])
        self.assertEqual((tagged, counted), (1, 1))
        self.assertError(check_gitlab(pairs, report, self.audit_auth_diff(), self.audit_auth_state()),
                         "summary line missing or mis-tagged for src/auth.js:3-4")

    def test_gitlab_removed_line_with_a_new_line_fails(self):
        pairs = copy.deepcopy(self.gl)
        pairs[1][1]["position"]["new_line"] = 3
        self.assertError(self.gl_errors(pairs), "removed line takes old_line only: src/auth.js:3")

    def test_github_old_side_context_location_anchors_on_last_removed_line(self):
        report = self.report.replace("`src/auth.js:3`", "`src/auth.js:3-4`")
        pairs = parse_pairs(read("github-dry-run.md").replace("src/auth.js:3", "src/auth.js:3-4"))
        self.assertEqual(check_github(pairs, report, self.diff, self.gh_state), [])

    def test_github_left_range_ending_on_context_fails(self):
        report = self.report.replace("`src/auth.js:3`", "`src/auth.js:3-4`")
        pairs = parse_pairs(read("github-dry-run.md").replace("src/auth.js:3", "src/auth.js:3-4"))
        auth = pairs[0][1]["comments"][1]
        auth.pop("line")
        auth.update(start_line=3, start_side="LEFT", line=4, side="LEFT")
        self.assertError(check_github(pairs, report, self.diff, self.gh_state),
                         "comment src/auth.js:4 (LEFT) is not on a diff line")


if __name__ == "__main__":
    unittest.main()
