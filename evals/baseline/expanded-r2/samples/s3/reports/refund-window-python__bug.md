**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule of `is_refundable` as the refund policy describes it (request, `policy/refund-policy.md`).
**Requirements:** 2 met, 1 not met, 0 not judged.
- Met — an order with `delivered_at` of `None` cannot be refunded through `is_refundable` (`policy/refund-policy.md`): `shop/refunds.py:9-10` returns `False` when `order.delivered_at is None`.
- Met — `is_refundable(order, now)` returns `True` when a refund can be granted and `False` otherwise (`policy/refund-policy.md`): `shop/refunds.py:8-12` returns a `bool` on every path.
- Not met — the 30-day window starts at delivery, not at placement, and a request exactly 30 days after delivery is still accepted (`policy/refund-policy.md`): `shop/refunds.py:12` measures the window from `order.created_at`. The inclusive `<=` is right, but the start of the window is wrong. See the Potential Bugs finding.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- `is_refundable` is a small pure function. It takes `now` as a parameter instead of calling `datetime.now()`, so it is easy to test.
- The window is a named constant (`REFUND_WINDOW`), and the comparison is inclusive (`<=`), which matches "exactly 30 days is still accepted".
- The undelivered-order guard is tested, and the tests use `Order` the way the existing `tests/test_orders.py` does.

## Findings

### Potential Bugs — Warning

**Location:** `shop/refunds.py:12`
**Issue:** The refund window is measured from `order.created_at`. `policy/refund-policy.md:7` says it starts at delivery (`Order.delivered_at`), "not when it was placed".
**Evidence:**
- Trigger: an order is placed on 2026-03-01 09:00 and delivered on 2026-03-10 09:00. The customer asks for a refund on 2026-04-09 09:00, exactly 30 days after delivery, which the policy says is still accepted.
- Effect: `now - order.created_at` is 39 days, which is more than `REFUND_WINDOW`, so `is_refundable` returns `False` and the refund is wrongly refused.
- Reach: every order delivered more than 0 days after it was placed loses that many days of its window. The delivery date is only used for the `None` check.
- Verification: I read `policy/refund-policy.md` and the `Order` dataclass in `shop/orders.py`. The only caller in the diff is the new test, and no other code or guard changes the result.

**Confidence:** High
**Fix:** Measure from delivery: `return now - order.delivered_at <= REFUND_WINDOW`. The `None` guard above it already narrows the type.

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:15-17`
**Issue:** The positive test cannot tell "30 days from delivery" apart from "30 days from placement". It delivers the order one day after placing it. No test covers the 30-day boundary or a request after the window.
**Evidence:**
- Trigger: `test_refund_on_the_next_day_is_accepted` passes with the current code, because the two start dates are one day apart and the request is far inside the window.
- Effect: the suite stays green while the Warning above is present, and nothing guards the inclusive boundary or the expired case.

**Confidence:** High
**Fix:** Add three cases. The first is an order delivered 9 days after placement, with a request exactly 30 days after delivery, expected `True`. The second is a request 30 days and 1 second after delivery, expected `False`. The third is a request after placement plus 30 days but inside the delivery window, expected `True`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 1       | 0          |     |
| Accessibility         |          |         |            | N/A |
| Observability         |          |         |            | N/A |
| API Design            |          |         |            | N/A |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **1**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `tests/test_refunds.py` covers an undelivered order (`False`) and a request one day after delivery (`True`). It leaves out the 30-day boundary, a request after the window, and any order delivered days after it was placed. Execution: not run.
**Look first:** `shop/refunds.py` (the window is measured from `created_at` instead of `delivered_at`), `tests/test_refunds.py` (the positive test cannot detect the wrong start date).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:stacks/python.md`, `tests/test_orders.py`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
