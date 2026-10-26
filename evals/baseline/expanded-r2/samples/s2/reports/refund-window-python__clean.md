**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule of `policy/refund-policy.md` as `is_refundable(order, now)` (request, `policy/refund-policy.md`).
**Requirements:** 4 met, 0 not met, 0 not judged.
- Met — the 30-day window starts at delivery (`Order.delivered_at`), not at placement (`policy/refund-policy.md`): `shop/refunds.py:12` measures `now - order.delivered_at` and never reads `created_at`. `shop/refunds.py:5` sets the window to 30 days.
- Met — a request exactly 30 days after delivery is accepted (`policy/refund-policy.md`): `shop/refunds.py:12` compares with `<=`.
- Met — an undelivered order (`delivered_at` is `None`) is not refundable through `is_refundable` (`policy/refund-policy.md`): `shop/refunds.py:9-10` returns `False` before the date arithmetic.
- Met — `is_refundable(order, now)` returns `True` or `False` (`policy/refund-policy.md`): `shop/refunds.py:8-12` returns `False` or the result of a comparison, which is always a `bool`.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- The window is a named constant, `REFUND_WINDOW`, so the policy value has one definition.
- The `None` guard comes first, so an undelivered order never reaches the date arithmetic.
- `now` is a parameter, so the function is pure and easy to test.
- The docstring points to the policy file, and the signature is fully type-hinted.
- The boundary uses `<=`, which matches the "exactly 30 days is still accepted" rule.

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:15-17`
**Issue:** The tests cover only the undelivered case and a refund one day after delivery. They do not cover the refused case or the exact-30-day boundary, which are the two behaviors the policy states most precisely.
**Evidence:** Change `<=` to `<` at `shop/refunds.py:12` (a request exactly 30 days after delivery is now refused, against policy rule 1), or make the function return `True` for any delivered order → both tests still pass, because they only check `None` → `False` and a refund one day after delivery → `True`.
**Confidence:** High
**Fix:** Add three cases. A request exactly 30 days after delivery (for example delivered `datetime(2026, 3, 2, 9, 0)` and `now` `datetime(2026, 4, 1, 9, 0)`) must return `True`. A request one second past 30 days must return `False`. A request after a long time, such as 90 days, must return `False`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         |          |         |            | N/A |
| Observability         |          |         |            | N/A |
| API Design            |          |         |            | N/A |
| Resilience            | 0        | 0       | 0          |     |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test_undelivered_order_is_not_refundable` covers rule 2 (`None` → `False`), and `test_refund_on_the_next_day_is_accepted` covers one accepted refund inside the window. They leave out the exact-30-day boundary and any refused case past the window. Execution: not run.
**Look first:** `tests/test_refunds.py` (boundary and expired cases are untested), `shop/refunds.py` (the window comparison that implements the refund rule).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:references/resilience.md`, `skill:stacks/python.md`, `tests/test_orders.py`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Resilience, Stack-Specific.
**Not verified:** nothing.
