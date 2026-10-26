**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule of `policy/refund-policy.md`: `is_refundable(order, now)` says whether a delivered order is still inside the 30-day refund window (request, `policy/refund-policy.md`).
**Requirements:** 1 met, 2 not met, 0 not judged.
- Met — an order with `delivered_at` of `None` is not refundable through `is_refundable` (`policy/refund-policy.md`, rule 2): `shop/refunds.py:10-11` returns `False` in that case.
- Not met — the 30-day window starts at delivery, not at placement, and a request exactly 30 days after delivery is accepted (`policy/refund-policy.md`, rule 1): `shop/refunds.py:12` measures the window from `order.created_at`, not `delivered_at`.
- Not met — `is_refundable` returns `True` when a refund can be granted and `False` otherwise (`policy/refund-policy.md`, rule 3): because of the wrong start date at `shop/refunds.py:12`, it returns `False` for orders that can still be refunded.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- `is_refundable` is a small pure function. It takes `now` as a parameter, so it is deterministic and easy to test.
- The window is a named constant (`REFUND_WINDOW`).
- The comparison is inclusive (`<=`), which matches the policy's "exactly 30 days is still accepted".
- The undelivered case is handled explicitly and tested.

## Findings

### Potential Bugs — Warning

**Location:** `shop/refunds.py:12`
**Issue:** The refund window is measured from `order.created_at`. The policy says it starts at delivery (`Order.delivered_at`). The docstring cites that policy, but the code does not follow it.
**Evidence:** An order is created on 2026-03-01 and delivered on 2026-03-25. `is_refundable(order, datetime(2026, 4, 5))` computes `now - created_at` = 35 days, which is more than 30, so it returns `False`. The customer is 11 days past delivery, so the policy says the refund must be accepted, and a valid refund is refused. The same happens at the exact boundary: an order delivered on 2026-03-02 09:00 and requested on 2026-04-01 09:00 is exactly 30 days after delivery, but 31 days after creation, so it returns `False`. `delivered_at` is never greater than `created_at`, so every order with a delivery delay loses that many days of its window. Verification checked the policy, the `Order` dataclass and the tests. `is_refundable` has no callers yet. The only test that exercises the window uses a one-day delivery delay, so it passes either way and does not refute this.
**Confidence:** High
**Fix:** Measure from delivery: `return now - order.delivered_at <= REFUND_WINDOW`. The `None` guard above it already narrows the type.

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:15-17`
**Issue:** The tests do not cover the window rule. The only delivered-order test has `now` one day after delivery and a delivery date one day after placement. It never checks an order past the window, the exact 30-day boundary, or a case where measuring from delivery and from creation give different answers.
**Evidence:** Changing `shop/refunds.py:12` back and forth between `created_at` and `delivered_at` leaves both tests green, so the wrong start date above went unnoticed.
**Confidence:** High
**Fix:** Add three cases. First, `now` exactly 30 days after `delivered_at` returns `True`. Second, `now` just over 30 days after `delivered_at` returns `False`. Third, an order delivered long after creation, requested within 30 days of delivery but more than 30 days after creation, returns `True`.

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
**Relevant tests:** changed — `tests/test_refunds.py` covers an undelivered order (`False`) and a refund one day after delivery (`True`). It leaves out the 30-day boundary, an expired window, and any order where delivery and creation dates differ enough to matter. Execution: not run.
**Look first:** `shop/refunds.py` (the window is measured from `created_at` instead of `delivered_at`), `tests/test_refunds.py` (no test of the window boundary or the start date).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:stacks/python.md`, `tests/test_orders.py`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
