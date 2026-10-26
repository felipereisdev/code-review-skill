Staged review of the refund rule is below. I'm not running the tests.

**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule of `policy/refund-policy.md` as `is_refundable(order, now)` (request, `policy/refund-policy.md`).
**Requirements:** 3 met, 0 not met, 0 not judged.
- Met — The window is 30 days from `Order.delivered_at`, and a request exactly 30 days after delivery is accepted (`policy/refund-policy.md`): `shop/refunds.py:5` sets the window to 30 days, and `shop/refunds.py:11` measures from `order.delivered_at` with `<=`, so exactly 30 days passes.
- Met — An undelivered order (`delivered_at` is `None`) is not refundable through `is_refundable` (`policy/refund-policy.md`): `shop/refunds.py:9-10` returns `False` for it.
- Met — `is_refundable(order, now)` returns `True` when a refund can be granted and `False` otherwise (`policy/refund-policy.md`): `shop/refunds.py:8-11` returns `False` for an undelivered order and the window comparison otherwise, so both branches give a `bool`.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- The implementation is a small pure function. `now` is passed in rather than read from the clock, so it is easy to test.
- The window is a named constant, `REFUND_WINDOW`. The comparison uses `<=`, which matches the policy's "exactly 30 days is still accepted".
- The docstring points to the policy file, and the `None` case has a test.

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:15-17`
**Issue:** The tests cover only an undelivered order and a refund one day after delivery. Neither the 30-day boundary nor a request after the window is tested. The boundary is the one detail the policy states explicitly.
**Evidence:** Changing `<=` to `<` at `shop/refunds.py:11` → a refund requested exactly 30 days after delivery is wrongly rejected, and both tests still pass. Likewise, changing `REFUND_WINDOW` to `timedelta(days=3650)` → every test still passes.
**Confidence:** High
**Fix:** Add three tests: `now = delivered_at + timedelta(days=30)` is `True`, `now = delivered_at + timedelta(days=30, seconds=1)` is `False`, and a date well after the window is `False`.

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
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `tests/test_refunds.py` covers an undelivered order (`False`) and a refund one day after delivery (`True`). It leaves out the exact 30-day boundary and any request after the window. Execution: not run.
**Look first:** `tests/test_refunds.py` (the 30-day boundary and the after-window case are untested), `shop/refunds.py` (the window comparison that the policy defines).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:stacks/python.md`, `tests/test_orders.py`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
