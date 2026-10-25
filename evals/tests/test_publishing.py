"""Offline shape tests for the --comment dry-run payloads that references/publishing.md describes."""
import copy
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
PAIR = re.compile(r"```sh\n(.*?)\n```\n\n```json\n(.*?)\n```", re.S)


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


def parse_pairs(text):
    return [(cmd, json.loads(payload)) for cmd, payload in PAIR.findall(text)]


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


if __name__ == "__main__":
    unittest.main()
