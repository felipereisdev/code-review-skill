**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule from `policy/refund-policy.md` as `is_refundable(order, now)` (request, `policy/refund-policy.md`).
**Requirements:** 3 met, 0 not met, 0 not judged.
- Met — The 30-day window starts at `Order.delivered_at`, and a request exactly 30 days after delivery is still accepted (`policy/refund-policy.md`): `shop/refunds.py:5` sets the window to 30 days. `shop/refunds.py:12` measures from `order.delivered_at` and uses `<=`, so a gap of exactly 30 days returns `True`.
- Met — An order with `delivered_at` of `None` is not refundable through `is_refundable` (`policy/refund-policy.md`): `shop/refunds.py:10-11` returns `False` before any date arithmetic.
- Met — `is_refundable(order, now)` returns `True` when a refund can be granted and `False` otherwise (`policy/refund-policy.md`): `shop/refunds.py:8` has the signature `(order: Order, now: datetime) -> bool`. Both return paths, at lines 11 and 12, give a `bool`.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- `is_refundable` is a small pure function. `now` is passed in rather than read from the clock, so it is easy to test.
- The 30-day window is a named constant (`REFUND_WINDOW`), and the docstring points to the policy file it implements.
- The code matches the policy on the two points where it is easy to go wrong: the window starts at delivery rather than at `created_at`, and the 30-day boundary is inclusive.
- The `None` case for undelivered orders is handled before the subtraction, so there is no `TypeError`.
- The tests build their data through a small `make_order` helper and use fixed dates, so they are deterministic.

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:12-17`
**Issue:** The tests do not cover the policy's boundary or the window-start rule, which are the points where `is_refundable` could go wrong. Nothing tests exactly 30 days after delivery, which the policy says is accepted. Nothing tests just past 30 days, which should be refused. Nothing tests an order delivered long after it was placed.
**Evidence:** Suppose a later edit changes `<=` to `<` at `shop/refunds.py:12`, or measures from `order.created_at` instead of `delivered_at`. `test_refund_on_the_next_day_is_accepted` still passes, because its delivery-to-request gap is 1 day and its creation-to-request gap is only 2 days. The regression would go unnoticed.
**Confidence:** High
**Fix:** Add three cases. First, `now == delivered_at + timedelta(days=30)` returns `True`. Second, `now == delivered_at + timedelta(days=30, seconds=1)` returns `False`. Third, an order placed more than 30 days before delivery but within 30 days of delivery returns `True`.

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
**Relevant tests:** changed — `tests/test_refunds.py` covers an undelivered order (`False`) and a refund one day after delivery (`True`). It leaves out the exact 30-day boundary, a request past 30 days, and an order delivered long after it was placed. Execution: not run.
**Look first:** `tests/test_refunds.py` (no boundary or past-window case), `shop/refunds.py` (the refund window logic).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:stacks/python.md`, `tests/test_orders.py`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
