**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule of `policy/refund-policy.md` as `is_refundable(order, now)` (request, `policy/refund-policy.md`).
**Requirements:** 2 met, 1 not met, 0 not judged.
- Not met — the 30-day refund window starts at delivery (`Order.delivered_at`), not at placement, and a request exactly 30 days after delivery is accepted (`policy/refund-policy.md`): `shop/refunds.py:12` measures `now - order.created_at`, so the window starts when the order was placed. The `<=` comparison does accept exactly 30 days, but from the wrong start date.
- Met — an order with `delivered_at` of `None` is not refundable through `is_refundable` (`policy/refund-policy.md`): `shop/refunds.py:10-11` returns `False` for it.
- Met — `is_refundable(order, now)` returns `True` when a refund can be granted and `False` otherwise (`policy/refund-policy.md`): `shop/refunds.py:9-12` returns `False` or the `bool` result of a comparison, and the signature is annotated `-> bool`.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- The change is small and focused: a named `REFUND_WINDOW` constant, a type-annotated signature, and `now` passed in as a parameter, which keeps the function pure and testable.
- The `delivered_at is None` guard handles the undelivered case up front, and a test covers it.
- The docstring points to the policy file that defines the rule.

## Findings

### Potential Bugs — Warning

**Location:** `shop/refunds.py:12`
**Issue:** The refund window is measured from `order.created_at` (when the order was placed). `policy/refund-policy.md` rule 1 says it starts at delivery (`Order.delivered_at`), "not when it was placed".
**Evidence:** An order placed 2026-03-01 and delivered 2026-03-25, with `is_refundable(order, datetime(2026, 4, 5))` called → `now - created_at` is 35 days, which is more than 30, so it returns `False`. The customer is 11 days after delivery, so the policy says the refund must be accepted. Any order delivered more than a few days after placement loses part of its window, and a slow delivery of more than 30 days loses all of it. Verification read `shop/orders.py` (`delivered_at` is `Optional[datetime]`, and it is non-`None` at this line because of the guard on lines 10-11) and the existing tests; none of them exercises a gap between placement and delivery that would catch this.
**Confidence:** High
**Fix:** Measure from delivery: `return now - order.delivered_at <= REFUND_WINDOW`.

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:11-17`
**Issue:** The only accepted-refund test delivers the order one day after placement and asks the next day, so it passes whether the window starts at placement or at delivery. No test covers the policy's boundary (exactly 30 days after delivery accepted, just over 30 days rejected) or a delivery that comes long after placement.
**Evidence:** A test with `created_at` 2026-03-01, `delivered_at` 2026-03-25 and `now` 2026-04-05 expecting `True` would fail against the current code, but no such test exists, so the bug in `shop/refunds.py:12` passes the suite.
**Confidence:** High
**Fix:** Add tests for exactly 30 days after delivery (`True`), 30 days and 1 second after delivery (`False`), and a delivery long after placement (`True`).

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 1       | 0          |     |
| Accessibility         | 0        | 0       | 0          | N/A |
| Observability         | 0        | 0       | 0          | N/A |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **1**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `tests/test_refunds.py` covers an undelivered order returning `False` and a refund the day after delivery returning `True`; it leaves out the 30-day boundary and a delivery long after placement. Execution: not run.
**Look first:** `shop/refunds.py` (the window is measured from `created_at` instead of `delivered_at`), `tests/test_refunds.py` (the accepted-refund test passes with either start date).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:stacks/python.md`, `tests/test_orders.py`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
