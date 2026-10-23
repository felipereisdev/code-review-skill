import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from score import looks_like_report, parse_findings, score_bug, score_clean, stack_mentioned  # noqa: E402

SKILL_FORMAT = """\
Some intro text.

### Security — Critical

**File:** `app/Http/Controllers/UserSearchController.php:18`
**Issue:** SQL injection: the search term is interpolated into raw SQL.
**Fix:** Use query bindings.

### Tests — Suggestion

**File:** `tests/Feature/UserSearchTest.php:30`
**Issue:** Add a test with quotes in the search term.
**Fix:** Add a test.

## Summary

| Category | Critical | Warning | Suggestion | N/A |
|----------|----------|---------|------------|-----|
| Security | 1        | 0       | 0          |     |
"""

NEW_FORMAT = """\
## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** The gift recipient lookup can return undefined.
**Evidence:** `giftRecipientId: 99` is not in the map → `recipient.name` throws a TypeError.
**Confidence:** High
**Fix:** Return null when the recipient is missing.

## Needs human verification

### Concurrency — Warning

**Location:** `src/labels.js:20-22`
**Issue:** The label counter is not incremented atomically.
**Evidence:** Two parallel calls both read 4 and write 5 → one label number is reused.
**Confidence:** Medium
**Fix:** Use an atomic increment.

## Summary

| Category | Critical | Warning | Suggestion | N/A |
|----------|----------|---------|------------|-----|
| Potential Bugs | 1 | 0 | 0 |  |
"""


COMPACT_FORMAT = """\
- app/Http/Controllers/UserSearchController.php:18: Critical: SQL injection: the search term is interpolated into raw SQL → use query bindings
- tests/Feature/UserSearchTest.php:30-34: Suggestion: no test with quotes in the search term → add one

## Needs human verification

- routes/api.php:12: Warning: the search route has no rate limit → add throttle middleware
"""

SQLI_LINE = ("app/Http/Controllers/UserSearchController.php:18: Critical: SQL injection: "
             "the search term is interpolated into raw SQL → use query bindings")


class ParseFindingsTest(unittest.TestCase):
    def test_skill_output_format(self):
        findings = parse_findings(SKILL_FORMAT)
        self.assertEqual([(f["heading"], f["severity"]) for f in findings],
                         [("Security — Critical", "Critical"), ("Tests — Suggestion", "Suggestion")])
        self.assertIn("SQL injection", findings[0]["text"])

    def test_bracketed_heading(self):
        report = "### [Potential Bugs] — [Warning]\n\n**File:** `src/labels.js:9`\n**Issue:** x\n"
        self.assertEqual(parse_findings(report)[0]["severity"], "Warning")

    def test_severity_inherited_from_parent_heading(self):
        report = "## CRITICAL ISSUES\n\n### Unbounded query\n- **File:** `a.php:1`\n- **Issue:** x\n"
        self.assertEqual([(f["heading"], f["severity"]) for f in parse_findings(report)],
                         [("Unbounded query", "Critical")])

    def test_severity_line_in_body(self):
        report = "### Unchecked lookup\n\n**Severity:** Warning\n**File:** `src/labels.js:9`\n**Issue:** x\n"
        self.assertEqual(parse_findings(report)[0]["severity"], "Warning")

    def test_empty_severity_section_is_not_a_finding(self):
        self.assertEqual(parse_findings("## Critical\n\nNone.\n\n## Warning\n\nNone found.\n"), [])

    def test_summary_table_is_not_a_finding(self):
        self.assertEqual(parse_findings("## Summary\n\n| Category | Critical | Warning |\n| Security | 1 | 0 |\n"), [])

    def test_headings_inside_code_fences_are_ignored(self):
        fence = "`" * 3
        report = fence + "\n### Security — Critical\n\n**File:** `a.php:1`\n**Issue:** x\n" + fence + "\n"
        self.assertEqual(parse_findings(report), [])

    def test_inherited_severity_resets_at_sibling_section(self):
        report = ("## Warnings\n\n### A\n**File:** `a.js:1`\n**Issue:** x\n\n"
                  "## Notes\n\n### B\n**File:** `b.js:1`\n**Issue:** y\n")
        self.assertEqual([f["heading"] for f in parse_findings(report)], ["A"])

    def test_block_without_file_or_issue_line_is_not_a_finding(self):
        self.assertEqual(parse_findings("### Security — Warning\n\nLooks fine overall.\n"), [])

    def test_location_evidence_confidence_format(self):
        finding = parse_findings(NEW_FORMAT)[0]
        self.assertEqual((finding["heading"], finding["severity"], finding["needs_verification"]),
                         ("Potential Bugs — Critical", "Critical", False))
        self.assertIn("TypeError", finding["text"])

    def test_needs_human_verification_findings_are_flagged(self):
        self.assertEqual([(f["heading"], f["needs_verification"]) for f in parse_findings(NEW_FORMAT)],
                         [("Potential Bugs — Critical", False), ("Concurrency — Warning", True)])

    def test_verification_heading_variants_are_recognized(self):
        report = ("### Needs Human Verification (Medium confidence)\n\n"
                  "#### Concurrency — Warning\n**Location:** `a.js:1`\n**Issue:** x\n")
        self.assertEqual([f["needs_verification"] for f in parse_findings(report)], [True])

    def test_verification_flag_resets_at_sibling_section(self):
        report = ("## Needs human verification\n\n### A — Warning\n**Location:** `a.js:1`\n**Issue:** x\n\n"
                  "## More findings\n\n### B — Warning\n**Location:** `b.js:1`\n**Issue:** y\n")
        self.assertEqual([(f["heading"], f["needs_verification"]) for f in parse_findings(report)],
                         [("A — Warning", True), ("B — Warning", False)])

    def test_old_file_format_is_never_flagged(self):
        self.assertEqual([f["needs_verification"] for f in parse_findings(SKILL_FORMAT)], [False, False])


class CompactFormatTest(unittest.TestCase):
    def test_compact_lines_are_findings(self):
        findings = parse_findings(COMPACT_FORMAT)
        self.assertEqual([(f["severity"], f["needs_verification"], f["compact"]) for f in findings],
                         [("Critical", False, True), ("Suggestion", False, True), ("Warning", True, True)])
        self.assertEqual(findings[0]["heading"], SQLI_LINE)
        self.assertEqual(findings[0]["text"], SQLI_LINE)

    def test_compact_line_decorations(self):
        report = ("* `src/a.js:9-12`: **Warning**: x is never reset → reset it\n"
                  "src/b.py:3: critical: y crashes on empty input → guard it\n")
        self.assertEqual([(f["heading"], f["severity"]) for f in parse_findings(report)],
                         [("`src/a.js:9-12`: **Warning**: x is never reset → reset it", "Warning"),
                          ("src/b.py:3: critical: y crashes on empty input → guard it", "Critical")])

    def test_compact_paths_with_brackets_parentheses_and_spaces(self):
        lines = ["src/app/users/[id]/page.tsx:9: Warning: empty data loses the selected user → guard it",
                 "src/app/(auth)/login/page.tsx:9: Critical: missing guard crashes → reject it",
                 "`src/my file.py:9`: Warning: empty input returns the wrong result → guard it"]
        report = "".join("- " + line + "\n" for line in lines)
        self.assertEqual([(f["heading"], f["severity"]) for f in parse_findings(report)],
                         [(lines[0], "Warning"), (lines[1], "Critical"), (lines[2], "Warning")])

    def test_compact_only_report_with_unusual_path_is_scored(self):
        report = "- src/app/(auth)/login/page.tsx:9: Critical: missing guard crashes → reject it\n"
        self.assertTrue(looks_like_report(report))
        self.assertEqual(score_bug(report, ["missing guard", r"\(auth\)"], "Critical"),
                         {"detected": True,
                          "matched_finding": "src/app/(auth)/login/page.tsx:9: Critical: missing guard crashes → reject it"})
        self.assertEqual(score_clean(report), {"false_positives": 1})

    def test_lines_that_only_look_compact_are_ignored(self):
        fence = "`" * 3
        report = ("Meeting at 10:30: Warning: deploy freeze\n"
                  "src/a.js: Warning: no line number\n"
                  "Warning: src/a.js:9 is wrong\n"
                  "| src/a.js:9 | Warning | x |\n"
                  + fence + "\nsrc/a.js:9: Critical: inside a fence\n" + fence + "\n")
        self.assertEqual(parse_findings(report), [])

    def test_full_format_findings_are_not_compact(self):
        self.assertEqual([f["compact"] for f in parse_findings(SKILL_FORMAT + NEW_FORMAT)], [False] * 4)

    def test_compact_scoring(self):
        self.assertEqual(score_bug(COMPACT_FORMAT, ScoreBugTest.PATTERNS, "Critical"),
                         {"detected": True, "matched_finding": SQLI_LINE})
        self.assertFalse(score_bug(COMPACT_FORMAT, ["rate limit"], "Suggestion")["detected"])
        self.assertEqual(score_clean(COMPACT_FORMAT), {"false_positives": 1})
        self.assertEqual(score_clean("## Needs human verification\n\n- src/a.js:9: Warning: x → y\n"),
                         {"false_positives": 0})
        self.assertTrue(looks_like_report(COMPACT_FORMAT))


class MarkdownFenceTest(unittest.TestCase):
    """Compact-shaped examples inside ordinary Markdown code fences are not findings."""

    EXAMPLE = ("- app/Http/Controllers/UserSearchController.php:18: Critical: "
               "SQL injection → bind parameters")
    PATTERNS = ["SQL injection", "UserSearchController"]

    def assert_example_ignored(self, report):
        self.assertEqual(parse_findings(report), [])
        self.assertFalse(looks_like_report(report))
        self.assertEqual(score_bug(report, self.PATTERNS, "Critical"),
                         {"detected": False, "matched_finding": None})
        self.assertEqual(score_clean(report), {"false_positives": 0})

    def test_tilde_fenced_compact_example_is_ignored(self):
        self.assert_example_ignored("Example syntax only:\n~~~text\n" + self.EXAMPLE + "\n~~~\n")

    def test_indented_backtick_fenced_compact_example_is_ignored(self):
        self.assert_example_ignored("Example syntax only:\n  ```text\n" + self.EXAMPLE + "\n  ```\n")

    def test_tilde_fenced_heading_is_ignored(self):
        report = "~~~\n### Security — Critical\n\n**Location:** `a.php:1`\n**Issue:** x\n~~~\n"
        self.assertEqual(parse_findings(report), [])

    def test_passed_line_inside_tilde_fence_is_not_a_report(self):
        self.assertFalse(looks_like_report("~~~\nCode review passed — no issues found.\n~~~\n"))

    def test_fence_does_not_hide_findings_after_it_closes(self):
        report = ("~~~\n" + self.EXAMPLE + "\n~~~\n"
                  "- src/a.js:9: Warning: real finding → fix it\n")
        self.assertEqual([f["heading"] for f in parse_findings(report)],
                         ["src/a.js:9: Warning: real finding → fix it"])

    def test_a_longer_closing_fence_closes_the_block(self):
        report = "~~~~\n" + self.EXAMPLE + "\n~~~~~\n"
        self.assertEqual(parse_findings(report), [])

    def test_a_different_fence_character_does_not_close_the_block(self):
        report = "~~~\n~~~not a close\n" + self.EXAMPLE + "\n~~~\n"
        self.assertEqual(parse_findings(report), [])


class ScoreBugTest(unittest.TestCase):
    PATTERNS = ["sql[ -]?injection|injection", "UserSearchController"]

    def test_detected_when_one_finding_matches_all_patterns(self):
        self.assertEqual(score_bug(SKILL_FORMAT, self.PATTERNS, "Critical"),
                         {"detected": True, "matched_finding": "Security — Critical"})

    def test_patterns_are_case_insensitive(self):
        self.assertTrue(score_bug(SKILL_FORMAT, ["SQL INJECTION", "usersearchcontroller"], "Warning")["detected"])

    def test_not_detected_below_min_severity(self):
        report = SKILL_FORMAT.replace("### Security — Critical", "### Security — Suggestion")
        self.assertEqual(score_bug(report, self.PATTERNS, "Warning"), {"detected": False, "matched_finding": None})

    def test_needs_human_verification_findings_do_not_count(self):
        report = NEW_FORMAT.replace("## Findings", "## Needs human verification", 1)
        self.assertEqual(score_bug(report, ["TypeError"], "Warning"), {"detected": False, "matched_finding": None})
        self.assertEqual(score_bug(NEW_FORMAT, ["TypeError"], "Warning"),
                         {"detected": True, "matched_finding": "Potential Bugs — Critical"})

    def test_patterns_must_match_the_same_finding(self):
        report = ("### Security — Critical\n**File:** `a.php:1`\n**Issue:** SQL injection.\n\n"
                  "### Naming — Warning\n**File:** `UserSearchController.php:1`\n**Issue:** bad name.\n")
        self.assertFalse(score_bug(report, self.PATTERNS, "Warning")["detected"])


class ScoreCleanTest(unittest.TestCase):
    def test_counts_critical_and_warning_only(self):
        self.assertEqual(score_clean(SKILL_FORMAT), {"false_positives": 1})

    def test_needs_human_verification_findings_are_not_false_positives(self):
        self.assertEqual(score_clean(NEW_FORMAT), {"false_positives": 1})

    def test_passed_review_has_no_false_positives(self):
        self.assertEqual(score_clean("Code review passed — no issues found."), {"false_positives": 0})


VERIFICATION_LINE = "**Verification:** 3 Critical/Warning candidates checked, 1 refuted.\n"


class VerificationLineTest(unittest.TestCase):
    def test_verification_line_after_summary_is_not_a_finding(self):
        self.assertEqual(parse_findings(SKILL_FORMAT + "\n" + VERIFICATION_LINE), parse_findings(SKILL_FORMAT))

    def test_compact_report_ending_with_verification_line(self):
        report = ("- src/a.ts:3: Warning: x is unset → guard it\n\n## Needs human verification\n\n"
                  "- src/b.ts:9: Warning: y may race → lock it\n\n" + VERIFICATION_LINE)
        findings = parse_findings(report)
        self.assertEqual([(f["compact"], f["needs_verification"]) for f in findings], [(True, False), (True, True)])

    def test_passed_report_with_verification_line_is_clean(self):
        report = "**Code review passed — no issues found.**\n\n" + VERIFICATION_LINE
        self.assertEqual(parse_findings(report), [])
        self.assertTrue(looks_like_report(report))
        self.assertEqual(score_clean(report), {"false_positives": 0})


class ReportShapeTest(unittest.TestCase):
    def test_finding_or_passed_confirmation_is_a_report(self):
        self.assertTrue(looks_like_report(SKILL_FORMAT))
        self.assertTrue(looks_like_report("**Code review passed — no issues found.**"))
        self.assertTrue(looks_like_report("Detected stack: Node.js\n\nCode review passed — no issues found.\n\n## Summary\n"))
        self.assertTrue(looks_like_report("### Security — Warning\n**File:** `a.js:1`\n**Issue:** x\n"))

    def test_report_with_only_verification_findings_is_a_report(self):
        self.assertTrue(looks_like_report("## Needs human verification" + NEW_FORMAT.split("## Needs human verification")[1]))

    def test_question_or_empty_output_is_not_a_report(self):
        self.assertFalse(looks_like_report("What would you like to review?\n\n1. Uncommitted changes"))
        self.assertFalse(looks_like_report(""))

    def test_bare_summary_echo_or_quoted_confirmation_is_not_a_report(self):
        fence = "`" * 3
        self.assertFalse(looks_like_report("## Summary\n"))
        self.assertFalse(looks_like_report("What would you like to review?\n\n## Summary\n"))
        self.assertFalse(looks_like_report("You are running inside an automated evaluation.\n4. Your final message ...\n\n## Summary\n"))
        self.assertFalse(looks_like_report('If no issues are found, state: **"Code review passed — no issues found."**\n'))
        self.assertFalse(looks_like_report(fence + "\nCode review passed — no issues found.\n" + fence + "\n"))

    def test_stack_mentioned(self):
        self.assertTrue(stack_mentioned("Detected stack: Laravel 11 (PHP)", "laravel"))
        self.assertTrue(stack_mentioned("Node.js project", "node"))
        self.assertFalse(stack_mentioned("A Python project", "laravel"))


if __name__ == "__main__":
    unittest.main()
