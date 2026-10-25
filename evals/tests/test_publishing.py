"""Offline shape tests for the --comment dry-run payloads that references/publishing.md describes."""
import copy
import hashlib
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from score import parse_findings  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "publishing")
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
    text outside the fences.
    """
    lines, pairs, i = text.split("\n"), [], 0
    while i < len(lines):
        if not lines[i].lstrip().startswith(FENCES):
            if CLI.search(lines[i]):
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
        match = next((f for f in findings if f["path"] == item["path"] and f["end"] == item["end"]
                      and anchor(f, diff) == item["side"]), None)
        where = f"{item['path']}:{item['end']} ({item['side']})"
        if match is None:
            errors.append(f"comment {where} matches no inline finding")
            continue
        loc = match["loc"]
        seen.add(loc)
        if item["start"] != match["start"]:
            errors.append(f"comment range does not match {loc}")
        if own_commented(match, item["side"], own):
            errors.append(f"inline comment for {loc} repeats the skill's own comment")
        body = item["body"]
        if not body.startswith(f"**{match['severity']} — {match['category']}** · `{loc}`"):
            errors.append(f"inline comment header does not match {loc}")
        if FINDING_MARKER not in body:
            errors.append(f"inline comment without the finding marker: {loc}")
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


def check_summary(body, report, findings, needs, diff, own, inline_count):
    errors = []
    if body.split("\n", 1)[0] != SUMMARY_MARKER:
        errors.append("summary marker missing")
    counts = [sum(f["severity"] == s for f in findings) for s in ("Critical", "Warning", "Suggestion")]
    want = "**Findings:** {} Critical, {} Warning, {} Suggestion. Inline comments: {}.".format(*counts, inline_count)
    if want not in body:
        errors.append("summary counts do not match the report")
    lines = body.split("\n")
    for f in findings:
        side = anchor(f, diff)
        tag = "not on a diff line" if side is None else (
            "already commented" if own_commented(f, side, own) else "inline")
        if not any(line.startswith(f"- {f['loc']}: {f['severity']}:") and line.endswith(f"({tag})") for line in lines):
            errors.append(f"summary line missing or mis-tagged for {f['loc']}")
    for f in needs:
        if not any(line.startswith(f"- {f['loc']}: {f['severity']}:") for line in lines):
            errors.append(f"summary misses needs-verification finding {f['loc']}")
    verification = re.search(r"^\*\*Verification:\*\* .*$", report, re.M)
    if verification is None or verification.group(0) not in body:
        errors.append("summary misses the verification line")
    return errors


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
        key = "right" if side == "RIGHT" else "left"
        if side not in ("RIGHT", "LEFT") or not any(line in h[key] and start in h[key] for h in hunks):
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


def check_gitlab(pairs, report, diff_text, state):
    errors = check_common(pairs, (GITLAB_DISCUSSION, GITLAB_CREATE, GITLAB_EDIT))
    findings, needs = report_findings(report)
    diff = parse_diff(diff_text)
    refs = state["mr"]["diff_refs"]
    own = []
    for d in state["discussions"]:
        note = d["notes"][0]
        if note["author"]["username"] == state["username"] and FINDING_MARKER in note["body"]:
            pos = note["position"]
            new = pos.get("new_line")
            own.append((pos["new_path"], "RIGHT" if new is not None else "LEFT",
                        new if new is not None else pos.get("old_line"), note["body"]))
    items = []
    for cmd, payload in pairs:
        if not GITLAB_DISCUSSION.match(cmd):
            continue
        pos = payload.get("position", {})
        new, old = pos.get("new_line"), pos.get("old_line")
        side, line = ("RIGHT", new) if new is not None else ("LEFT", old)
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
        elif not any(h["left"].get(old) == "del" for h in hunks):
            item["error"] = f"comment {where} (LEFT) is not on a diff line"
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
     "a7ebaf3c6d850fef6cef04f4f724480701ef7bda274b6ece9c5dd5fe09386708", []),
    ("P02", "gitlab-dry-run.md", None,
     "f4884a6f21d3cecf16681464070c0335f39b5a51bb5d9592f799dbbb485d7394", []),
    ("P03", "github-dry-run.md", "write command without its JSON payload: gh pr review 42 --approve",
     "48ad127dadd5340f11f2c7f5b4c71627ee5139ccc7dd15e8be338a30d39ff61b",
     [("append", "", "\n```sh\ngh pr review 42 --approve\n```\n")]),
    ("P04", "gitlab-dry-run.md", "write command without its JSON payload: glab mr approve 42",
     "201c22bd0a1c054de78372605425aa47833c326f37f7b497588bed15839394a5",
     [("append", "", "\n```sh\nglab mr approve 42\n```\n")]),
    ("P05", "github-dry-run.md", "write command without its JSON payload: gh pr review 42 --approve",
     "faf833b0ad493f6017b997fd3d3331c51f4024157c2bc219fa5b6459c5945df8",
     [("replace", "### 2. Summary comment (edit 9007199254740993)",
       "```sh\ngh pr review 42 --approve\n```\n\n### 2. Summary comment (edit 9007199254740993)")]),
    ("P06", "gitlab-dry-run.md", "write command without its JSON payload: glab mr approve 42",
     "af02d462c5825324834d5fb21affb33154cccd3ddb8c1d44d5a6c4132410fc19",
     [("replace", "### 4. Summary comment (edit 502)",
       "```sh\nglab mr approve 42\n```\n\n### 4. Summary comment (edit 502)")]),
    ("P07", "github-dry-run.md", "write command without its JSON payload: " + GH_REVIEW_CMD,
     "5bf57876c2b6e5c7715697f1714247da3fc2fa5ca5ebfd853d6b264dcd799f78",
     [("append", "", "\n```sh\n" + GH_REVIEW_CMD + "\n```\n")]),
    ("P08", "gitlab-dry-run.md", "write command without its JSON payload: glab api --hostname gitlab.com --method PUT",
     "97ef276dc4ac538073163f8df19807ac89e725d3cdc5cd2c296399769e573d50",
     [("tail", "```json\n", "\n")]),
    ("P09", "github-dry-run.md", "unclosed fence: ```sh",
     "27f60e341281d79a9bad80bc75efdd9bc36780e5753d0e87700b7eecd4117525",
     [("append", "", "\n```sh\ngh pr review 42 --approve\n")]),
    ("P10", "gitlab-dry-run.md", "unclosed fence: ```json",
     "af8ed806de5f31c69c97ef65ad51d41e250c0f348727b612f8ad3cbc92ecaa82",
     [("append", "", "\n```sh\nglab api --hostname gitlab.com --method POST projects/77/merge_requests/42/discussions "
       + H + " --input discussion-1.json\n```\n\n```json\n{}\n")]),
    ("P11", "github-dry-run.md", "invalid JSON payload for: gh api --hostname github.com --method PATCH",
     "ef9c126dbdc8fedfee2e75fe1527540ab634f41f87d04910b7f49f574bf8d15e",
     [("tail", "```json\n", "```json\n{not-json}\n```\n")]),
    ("P12", "gitlab-dry-run.md", "write command without its JSON payload: glab api --hostname gitlab.com --method POST",
     "43269b0d1420a818b203a928d0c00db30dae913b8321ea1c3e7764193a2555ac",
     [("replace", GL_DISCUSSION_1, "--input discussion-1.json\n```\n\n```text\nintervening block\n```\n\n```json")]),
    ("P13", "gitlab-dry-run.md", "JSON payload without a write command",
     "fda4a05ef3b38e2828f5a4868da72ae516ca37788941a67752c382bfa530224d",
     [("append", "", "\n```json\n{}\n```\n")]),
    ("P14", "github-dry-run.md", "unsupported fence: ```bash",
     "482d72ced8b76c2c873a7186274d42d4dc04975e29c854c83dc6ea72a9bc33bd",
     [("append", "", "\n```bash\ngh pr review 42 --approve\n```\n")]),
    ("P15", "gitlab-dry-run.md", "unsupported fence: ```shell",
     "583b17686b227fbda32142a3e38f13b44921a43ab7c8c41e794cd17419381d44",
     [("append", "", "\n```shell\nglab mr approve 42\n```\n")]),
    ("P16", "github-dry-run.md", "unsupported fence: ````sh",
     "c11810a7a7428323e5a2d3597e076418306c2e0df353617b2e6f7c4e4d91e045",
     [("append", "", "\n````sh\ngh pr review 42 --approve\n````\n")]),
    ("P17", "github-dry-run.md", "unclosed fence: ```json",
     "250530dcded9fba56de8d0f606066f739da18575c76aedd28da0a3182173e9d2",
     [("tail", "\n```\n", "\n``\n")]),
    ("P18", "gitlab-dry-run.md", None,
     "050bad784304f38230043a0a83d49f40b38466eebd48a7ba8f5f4343eba6de84",
     [("replace", "## Dry run — nothing was published\n\n", "## Dry run — nothing was published\n\n\n\n"),
      ("replace", "\n\n### 2. Discussion on src/auth.js:3", "\n\n\n\n### 2. Discussion on src/auth.js:3")]),
    ("P19", "github-dry-run.md", None,
     "431043421cb871eed582f407e33bf45702a0d1e2fcf711ac2dcc38a21d72d87b",
     [("tail", "\n```\n", "\n```")]),
    ("P20", "gitlab-dry-run.md", "write command without its JSON payload: glab api --hostname gitlab.com --method POST",
     "080113dd0cf7c3dcd07186dacd986d77e7aed5a8350f55e07fbabd1a95be1177",
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
        for path in ("src/gh/index.js:9", "src/glab/index.js:9"):
            with self.subTest(path=path):
                pairs = parse_pairs(text.replace(heading, "### 1. Discussion on " + path))
                self.assertEqual(pairs, parse_pairs(text))
                self.assertEqual(check_gitlab(pairs, self.report, self.diff, self.gl_state), [])


if __name__ == "__main__":
    unittest.main()
