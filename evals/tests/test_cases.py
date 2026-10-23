"""Regression tests for the case expectations: planted bugs need real evidence.

Each case's ``pair.json`` decides when a review has detected the planted bug.
These tests pin both directions: an unrelated finding that happens to mention
the affected file or API must not earn credit, while the committed baseline
bug reports must still be detected.

The payment table holds every probe sentence used by the final review rounds
(waves 1 to 5) plus plural, passive and reordered variants of each concept, so
a future pattern edit cannot reopen a closed false positive or lose a genuine
allegation. Wave 5 pins the other direction of the test-context guard: a test
mention must only veto a coverage request, never a genuine false-success claim.

Wave 6 replaces probe archaeology with the frozen acceptance corpus: 100 rows
(52 DETECT, 48 IGNORE) copied verbatim from the review artifact into
``fixtures/payment_probes.json`` and scored through the real ``score.py`` and
``pair.json``. Those rows are the merge gate for this finding; new linguistic
variants do not expand it.
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


# Every payment probe: (name, expected heading or None, report body).
# The File line always points at the changed file, so the location group is
# satisfied in every probe and only the concept groups decide the result.
PAYMENT_PROBES = [
    # --- w1 negatives: success-path coverage and privacy guidance ---
    (
        "w1_success_path_amount",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:12`
**Issue:** Add a success-path test asserting the amount sent to the gateway.
**Fix:** Assert the fake gateway receives 500 cents.
""",
    ),
    (
        "w1_successful_charge_wording",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:12`
**Issue:** Add a success-path test proving the caller reports a successful charge with the returned chargeId.
**Fix:** Assert the returned chargeId is included in the caller response.
""",
    ),
    (
        "w1_privacy_discard_message",
        None,
        """### Security — Warning
**File:** `src/charge.ts:15-17`
**Issue:** The catch returns the raw gateway message to clients, exposing gateway internals.
**Fix:** Discard the raw provider message and return a stable public error code.
""",
    ),
    (
        "w1_error_classification",
        None,
        """### Potential Bugs / Security — Warning
**File:** `src/charge.ts:15-17`
**Issue:** The catch block turns every exception into `{ ok: false, error: message }`.
Callers cannot tell a decline from a transient outage, and the raw gateway message
is passed on as `error`.
**Fix:** Return a stable error code and rethrow unexpected errors.
""",
    ),
    # --- w2 negatives: reordered privacy advice ---
    (
        "w2_reordered_privacy",
        None,
        """### Security — Warning
**File:** `src/charge.ts:15-17`
**Issue:** The catch returns the raw gateway message to clients, exposing gateway internals.
**Fix:** Return a stable public error code and discard the raw provider message.
""",
    ),
    (
        "w2_discard_error_message",
        None,
        """### Security — Warning
**File:** `src/charge.ts:15-17`
**Issue:** The catch returns the raw gateway message to clients, exposing gateway internals.
**Fix:** Discard the error message and return a stable public error code.
""",
    ),
    # --- w3 negative: negated error inside correct success-path behaviour ---
    (
        "w3_negated_error_success_path",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:15`
**Issue:** Add a success-path test proving chargeInvoice treats a charge without an error as successful.
**Fix:** Assert the returned chargeId is included in the caller response.
""",
    ),
    # --- new negatives: coverage/test/happy-path contexts ---
    (
        "new_test_context_failed_charge_as_paid",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:15`
**Issue:** Add a test proving chargeInvoice treats a failed charge as paid.
**Fix:** Assert the paid status is returned.
""",
    ),
    (
        "new_success_path_context_declined_charge",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:15`
**Issue:** Cover the success path where a declined charge is reported as successful.
**Fix:** Assert the returned result.
""",
    ),
    (
        "new_happy_path_context_failed_charge",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:15`
**Issue:** The happy path test asserts a failed charge is reported as paid.
**Fix:** Assert the paid result instead of only the chargeId.
""",
    ),
    (
        "new_plural_errors_without_failure",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:15`
**Issue:** Add tests proving chargeInvoice reports a successful charge for a card without errors.
**Fix:** Cover the success path in `test/charge.test.ts`.
""",
    ),
    (
        "new_no_errors_success_path",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:15`
**Issue:** Add a success-path test asserting that chargeInvoice returns success when there are no errors.
**Fix:** Assert the chargeId is present.
""",
    ),
    (
        "new_without_any_errors_success_path",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:15`
**Issue:** Add a test proving a charge without any errors returns successfully.
**Fix:** Assert the returned chargeId.
""",
    ),
    (
        "new_reordered_privacy_plural",
        None,
        """### Security — Warning
**File:** `src/charge.ts:15-17`
**Issue:** The catch returns the raw gateway message to clients, exposing gateway internals.
**Fix:** Return a stable public error code and discard the raw provider messages.
""",
    ),
    # --- w1/w2 positives: explicit suppression or false success ---
    (
        "w1_swallowed_error_reported_as_success",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** The catch swallows the gateway error and returns `{ ok: true }`, so a
failed charge is reported as successful.
**Fix:** Return the `{ ok: false, error }` variant.
""",
    ),
    (
        "w2_failed_charge_treated_as_paid",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** A failed charge is treated as paid by chargeInvoice, even though the gateway rejected it.
**Fix:** Return the failure result to the caller.
""",
    ),
    (
        "w2_failed_charge_reported_as_paid",
        "Potential Bugs — Warning",
        """### Potential Bugs — Warning
**File:** `src/charge.ts:15`
**Issue:** The caller reports the failed charge as paid and marks the invoice settled.
**Fix:** Return the failure variant instead of the paid result.
""",
    ),
    # --- w3 positives: plural swallowed-error allegations (R2) ---
    (
        "w3_swallows_gateway_errors",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** The catch swallows gateway errors and returns a successful charge result.
**Fix:** Return the failure variant to the caller.
""",
    ),
    (
        "w3_swallows_exceptions",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** The catch swallows exceptions and returns success.
**Fix:** Return the failure variant to the caller.
""",
    ),
    # --- new positives: failure concept in plural, passive and reordered forms ---
    (
        "new_failure_plural_errors_passive",
        "Potential Bugs — Warning",
        """### Potential Bugs — Warning
**File:** `src/charge.ts:15`
**Issue:** Gateway errors are silently swallowed by the catch, so a successful charge is returned to the caller.
**Fix:** Propagate the error.
""",
    ),
    (
        "new_failure_plural_charge_failures",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** Charge failures are reported as successful payments to the caller.
**Fix:** Return the failure result.
""",
    ),
    (
        "new_failure_plural_payment_failures_passive",
        "Potential Bugs — Warning",
        """### Potential Bugs — Warning
**File:** `src/charge.ts:15`
**Issue:** All payment failures are discarded by chargeInvoice and reported as success.
**Fix:** Surface the failure instead of a success result.
""",
    ),
    (
        "new_failure_reordered_suppression",
        "Potential Bugs — Warning",
        """### Potential Bugs — Warning
**File:** `src/charge.ts:15`
**Issue:** The failed charge is discarded and the invoice is marked as paid.
**Fix:** Record the failure instead.
""",
    ),
    # --- new positives: suppression concept reordered / passive / plural ---
    (
        "new_suppression_reordered_declined_payment",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** Because the exception is swallowed, a declined payment is returned as successful.
**Fix:** Rethrow the exception.
""",
    ),
    (
        "new_suppression_reordered_after_failure",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** The payment is declined by the gateway, yet chargeInvoice records it as successful.
**Fix:** Return the failure result.
""",
    ),
    (
        "new_suppression_passive_plural",
        "Potential Bugs — Warning",
        """### Potential Bugs — Warning
**File:** `src/charge.ts:15`
**Issue:** All gateway errors are ignored and reported as a successful charge.
**Fix:** Return the error to the caller.
""",
    ),
    (
        "new_suppression_plural_dropped_errors",
        "Potential Bugs — Warning",
        """### Potential Bugs — Warning
**File:** `src/charge.ts:15`
**Issue:** Errors from the gateway are dropped by the catch; the invoice is marked paid.
**Fix:** Propagate them to the caller.
""",
    ),
    (
        "new_suppression_treated_as_paid",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** chargeInvoice treats every declined charge as paid, even though no money was collected.
**Fix:** Return the `{ ok: false }` variant.
""",
    ),
    (
        "new_real_allegation_with_test_in_fix",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** chargeInvoice treats a failed charge as paid.
**Fix:** Return the failure variant and add a regression test.
""",
    ),
    # --- w5 R3: a test mention must not veto a genuine false-success claim ---
    (
        "w5r3_test_suite_passes_failed_charge_as_paid",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** The test suite currently passes even though chargeInvoice treats a failed charge as paid.
**Fix:** Return the failure variant to the caller.
""",
    ),
    (
        "w5r3_tests_show_treated_as_paid",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** Tests show that a failed charge is treated as paid by chargeInvoice, even though the gateway rejected it.
**Fix:** Return the failure variant to the caller.
""",
    ),
    (
        "w5_test_mention_contrast_declined_payment",
        "Potential Bugs — Warning",
        """### Potential Bugs — Warning
**File:** `src/charge.ts:15`
**Issue:** Although the test suite passes, chargeInvoice records a declined payment as successful.
**Fix:** Record the decline instead.
""",
    ),
    (
        "w5_test_recommendation_after_allegation",
        "Potential Bugs — Critical",
        """### Potential Bugs — Critical
**File:** `src/charge.ts:15`
**Issue:** chargeInvoice reports a failed charge as paid; add a regression test for it.
**Fix:** Return the failure variant.
""",
    ),
    (
        "w5_no_test_for_failed_charge_branch",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:15`
**Issue:** No test covers chargeInvoice treating a failed charge as paid.
**Fix:** Add a case for the failure branch.
""",
    ),
    (
        "w5_cover_success_path_before_allegation",
        None,
        """### Tests/Coverage — Warning
**File:** `src/charge.ts:15`
**Issue:** Cover the success path where chargeInvoice treats a failed charge as paid.
**Fix:** Assert the paid result.
""",
    ),
]


PAYMENT_CORPUS_PATH = os.path.join(TESTS_DIR, "fixtures", "payment_probes.json")
PAYMENT_CORPUS_HEADER = "### Potential Bugs — Warning\n**File:** `src/charge.ts:15`\n"


def load_payment_corpus():
    with open(PAYMENT_CORPUS_PATH, encoding="utf-8") as corpus_file:
        return json.load(corpus_file)


class PaymentExpectationTest(unittest.TestCase):
    """Table of every review probe; concepts must match, phrasings must not."""

    def test_every_frozen_corpus_row_matches_its_label(self):
        bug = load_bug("swallowed-error-ts")
        corpus = load_payment_corpus()
        self.assertEqual(len(corpus), 100)
        self.assertEqual(sum(row["label"] == "DETECT" for row in corpus), 52)
        self.assertEqual(sum(row["label"] == "IGNORE" for row in corpus), 48)

        failures = []
        for row in corpus:
            report = PAYMENT_CORPUS_HEADER + row["detail"] + "\n"
            detected = score_bug(report, bug["patterns"], bug["min_severity"])["detected"]
            expected = row["label"] == "DETECT"
            if detected != expected:
                failures.append("%s expected %s, got detected=%s"
                                % (row["id"], row["label"], detected))
            with self.subTest(row=row["id"]):
                self.assertEqual(detected, expected,
                                 "%s must match %s" % (row["id"], row["label"]))
        self.assertEqual(failures, [], "%d/%d corpus rows failed:\n%s"
                         % (len(failures), len(corpus), "\n".join(failures)))

    def test_every_payment_probe_matches_its_expected_result(self):
        bug = load_bug("swallowed-error-ts")
        for name, expected_heading, report in PAYMENT_PROBES:
            with self.subTest(probe=name):
                result = score_bug(report, bug["patterns"], bug["min_severity"])
                if expected_heading is None:
                    self.assertEqual(result, {"detected": False, "matched_finding": None},
                                     "probe %s must not earn recall credit" % name)
                else:
                    self.assertEqual(result, {"detected": True, "matched_finding": expected_heading},
                                     "probe %s must be detected" % name)

    def test_xss_performance_warning_is_not_an_xss_finding(self):
        bug = load_bug("xss-react")
        report = """### Performance — Warning
**File:** `src/components/CommentList.tsx:9`
**Issue:** The newline replacement before dangerouslySetInnerHTML is repeated on
every render; memoize it for long comment bodies.
**Fix:** Cache the transformed string.
"""
        self.assertEqual(score_bug(report, bug["patterns"], bug["min_severity"]),
                         {"detected": False, "matched_finding": None})


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
