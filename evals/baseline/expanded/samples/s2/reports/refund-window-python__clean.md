**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule of the refund policy: `is_refundable(order, now)` (request, `policy/refund-policy.md`).
**Requirements:** 3 met, 0 not met, 0 not judged.
- Met — the window is 30 days from `Order.delivered_at`, and a request exactly 30 days after delivery is accepted (`policy/refund-policy.md`): `shop/refunds.py:5` sets `REFUND_WINDOW` to 30 days, and `shop/refunds.py:12` compares `now - order.delivered_at <= REFUND_WINDOW`. The window runs from delivery, and `<=` accepts the exact boundary.
- Met — an order with `delivered_at` of `None` is not refundable through `is_refundable` (`policy/refund-policy.md`): `shop/refunds.py:10-11` returns `False` for it.
- Met — `is_refundable(order, now)` returns `True` when a refund can be granted and `False` otherwise (`policy/refund-policy.md`): `shop/refunds.py:8-12` returns a `bool` on every path.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- The boundary uses `<=`, so "exactly 30 days is still accepted" holds, and the window is measured from `delivered_at`, not `created_at`, as the policy says.
- `now` is a parameter, not a call to `datetime.now()`. The function is pure and easy to test.
- The window is a named constant, and the `None` case returns early with the policy cited in the docstring.
- The change ships with tests, and they follow the style of `tests/test_orders.py`.

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:12-17`
**Issue:** The tests do not cover the rules the policy states most precisely: the exact 30-day boundary and the rejection of a request after the window. Both tests cover cases that are far from the limit.
**Evidence:** Change `<=` to `<` at `shop/refunds.py:12`. A request exactly 30 days after delivery is now refused, which breaks policy rule 1. `test_undelivered_order_is_not_refundable` and `test_refund_on_the_next_day_is_accepted` both still pass, because one ends before the window check and the other is 1 day after delivery. Nothing tests the `False` result for a delivered order, so an inverted or removed window check would also go unnoticed. The "starts at delivery, not at placement" rule is not discriminated either: `make_order` uses a `created_at` of 1 Mar and a `delivered_at` of 2 Mar, which are 1 day apart.
**Confidence:** High
**Fix:** Add tests for `now == delivered_at + timedelta(days=30)` (expects `True`), `now == delivered_at + timedelta(days=30, seconds=1)` (expects `False`), and a case where `created_at` is more than 30 days before `now` but `delivered_at` is recent (expects `True`).

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
**Relevant tests:** changed — `tests/test_refunds.py` covers an undelivered order (`False`) and a refund 1 day after delivery (`True`). It leaves out the exact 30-day boundary, a request after the window, and the delivery-versus-placement distinction. Execution: not run.
**Look first:** `shop/refunds.py` (the refund decision and the policy boundary), `tests/test_refunds.py` (the boundary and the post-window case are untested).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:stacks/python.md`, `tests/test_orders.py`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
