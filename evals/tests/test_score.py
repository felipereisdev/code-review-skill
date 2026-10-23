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
