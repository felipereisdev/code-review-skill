**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule of `policy/refund-policy.md` as `is_refundable(order, now)` (request, `policy/refund-policy.md`).
**Requirements:** 3 met, 0 not met, 0 not judged.
- Met — The window is 30 days from `Order.delivered_at`, and a request exactly 30 days after delivery is accepted (`policy/refund-policy.md`): `shop/refunds.py:5` sets the window to 30 days. `shop/refunds.py:12` measures from `delivered_at` and compares with `<=`, so a request exactly at 30 days returns `True`.
- Met — An order with `delivered_at` of `None` is not refundable through `is_refundable` (`policy/refund-policy.md`): `shop/refunds.py:10-11` returns `False` in that case.
- Met — `is_refundable(order, now)` returns `True` when a refund can be granted and `False` otherwise (`policy/refund-policy.md`): `shop/refunds.py:8-12` has that signature and returns only `bool` values.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- The function is small and pure. It takes `now` as a parameter instead of reading the clock, so it is deterministic and easy to test.
- The comparison uses `<=`, which follows the policy's "exactly 30 days is still accepted" rule. The window is a named constant, and the `delivered_at is None` case is handled before the subtraction.
- The tests pin the undelivered case and a delivered in-window case.

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:13-17`
**Issue:** The tests never exercise the refusal side of the window or its boundary. Both the `False` result for an expired order and the exact-30-day case in rule 1 are untested.
**Evidence:** A later edit changes `<=` to `<` on `shop/refunds.py:12`, or the window to a different value → `test_refund_on_the_next_day_is_accepted` (1 day) and the undelivered test still pass, so the policy's "exactly 30 days is still accepted" rule and the rejection after 30 days regress without a failing test.
**Confidence:** High
**Fix:** Add three cases built on `make_order`: `now == delivered_at + timedelta(days=30)` must be `True`, `now == delivered_at + timedelta(days=30, seconds=1)` must be `False`, and a request well past the window must be `False`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
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
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `tests/test_refunds.py` covers the undelivered order (`False`) and a refund one day after delivery (`True`). It leaves out the exact-30-day boundary and every expired case. Execution: not run.
**Look first:** `tests/test_refunds.py` (no boundary or expiry test for the 30-day rule), `shop/refunds.py` (the window comparison on line 12).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:stacks/python.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
