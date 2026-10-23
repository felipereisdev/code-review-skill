"""Regression tests for the case expectations: planted bugs need real evidence.

Each case's ``pair.json`` decides when a review has detected the planted bug.
These tests pin both directions: an unrelated finding that happens to mention
the affected file or API must not earn credit, while the committed baseline
bug reports must still be detected.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from score import score_bug  # noqa: E402


TESTS_DIR = os.path.dirname(os.path.realpath(__file__))
EVALS_DIR = os.path.dirname(TESTS_DIR)
CASES_DIR = os.path.join(EVALS_DIR, "cases")
BASELINE_DIR = os.path.join(EVALS_DIR, "baseline", "reports")


def load_bug(case):
    path = os.path.join(CASES_DIR, case, "pair.json")
    with open(path, encoding="utf-8") as pair_file:
        return json.load(pair_file)["bug"]


class UnrelatedFindingTest(unittest.TestCase):
    """A finding about the same file/API but a different problem is not recall."""

    def assert_not_detected(self, case, report):
        bug = load_bug(case)
        self.assertEqual(score_bug(report, bug["patterns"], bug["min_severity"]),
                         {"detected": False, "matched_finding": None})

    def test_payment_success_path_warning_is_not_a_swallowed_error(self):
        report = """### Tests/Coverage — Warning
**File:** `src/charge.ts:12`
**Issue:** Add a success-path test asserting the amount sent to the gateway.
**Fix:** Assert the fake gateway receives 500 cents.
"""
        self.assert_not_detected("swallowed-error-ts", report)

    def test_payment_success_charge_wording_is_not_a_swallowed_error(self):
        report = """### Tests/Coverage — Warning
**File:** `src/charge.ts:12`
**Issue:** Add a success-path test proving the caller reports a successful charge with the returned chargeId.
**Fix:** Assert the returned chargeId is included in the caller response.
"""
        self.assert_not_detected("swallowed-error-ts", report)

    def test_payment_privacy_discard_warning_is_not_a_swallowed_error(self):
        report = """### Security — Warning
**File:** `src/charge.ts:15-17`
**Issue:** The catch returns the raw gateway message to clients, exposing gateway internals.
**Fix:** Discard the raw provider message and return a stable public error code.
"""
        self.assert_not_detected("swallowed-error-ts", report)

    def test_payment_error_classification_warning_is_not_a_swallowed_error(self):
        report = """### Potential Bugs / Security — Warning
**File:** `src/charge.ts:15-17`
**Issue:** The catch block turns every exception into `{ ok: false, error: message }`.
Callers cannot tell a decline from a transient outage, and the raw gateway message
is passed on as `error`.
**Fix:** Return a stable error code and rethrow unexpected errors.
"""
        self.assert_not_detected("swallowed-error-ts", report)

    def test_xss_performance_warning_is_not_an_xss_finding(self):
        report = """### Performance — Warning
**File:** `src/components/CommentList.tsx:9`
**Issue:** The newline replacement before dangerouslySetInnerHTML is repeated on
every render; memoize it for long comment bodies.
**Fix:** Cache the transformed string.
"""
        self.assert_not_detected("xss-react", report)


class ErrorSuppressionFindingTest(unittest.TestCase):
    """A real error-suppression allegation must still be detected."""

    def test_swallowed_error_reported_as_success_is_detected(self):
        report = """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** The catch swallows the gateway error and returns `{ ok: true }`, so a
failed charge is reported as successful.
**Fix:** Return the `{ ok: false, error }` variant.
"""
        bug = load_bug("swallowed-error-ts")
        result = score_bug(report, bug["patterns"], bug["min_severity"])
        self.assertTrue(result["detected"])
        self.assertEqual(result["matched_finding"], "Potential Bugs — Critical")


class BaselineBugReportTest(unittest.TestCase):
    """Tightening the expectations must keep the measured detections."""

    def test_every_baseline_bug_report_still_matches_its_expectation(self):
        cases = sorted(
            name for name in os.listdir(CASES_DIR)
            if os.path.isfile(os.path.join(CASES_DIR, name, "pair.json"))
        )
        self.assertTrue(cases)

        for case in cases:
            report_path = os.path.join(BASELINE_DIR, case + "__bug.md")
            with self.subTest(case=case):
                self.assertTrue(os.path.isfile(report_path),
                                "missing baseline bug report: " + report_path)
                with open(report_path, encoding="utf-8") as report_file:
                    report = report_file.read()
                bug = load_bug(case)
                self.assertTrue(score_bug(report, bug["patterns"], bug["min_severity"])["detected"],
                                "baseline bug report no longer detected: " + case)


if __name__ == "__main__":
    unittest.main()
