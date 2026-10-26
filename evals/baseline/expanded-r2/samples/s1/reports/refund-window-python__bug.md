## Scope

**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule of `policy/refund-policy.md` as `is_refundable(order, now)` (request, `policy/refund-policy.md`).
**Requirements:** 2 met, 1 not met, 0 not judged.
- Not met — the 30-day refund window starts at delivery (`Order.delivered_at`), not at placement, and a request exactly 30 days after delivery is accepted (`policy/refund-policy.md`, rule 1): `shop/refunds.py:12` measures the window from `order.created_at`. The `<=` comparison is inclusive, but it is anchored to the wrong date.
- Met — an undelivered order (`delivered_at is None`) is not refundable through `is_refundable` (`policy/refund-policy.md`, rule 2): `shop/refunds.py:10-11` returns `False` in that case.
- Met — `is_refundable(order, now)` returns `True` when a refund can be granted and `False` otherwise (`policy/refund-policy.md`, rule 3): both return paths at `shop/refunds.py:11-12` give a `bool`.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- The window is a named constant (`REFUND_WINDOW`) with a `timedelta`, and the signature is fully type-hinted.
- The docstring points to the policy file.
- `now` is a parameter, not `datetime.now()`, so the function is pure and easy to test.
- The tests use a small `make_order` helper and cover the undelivered rule.

## Findings

### Potential Bugs — Warning

**Location:** `shop/refunds.py:12`
**Issue:** The refund window is measured from `order.created_at`. Rule 1 of `policy/refund-policy.md` says it starts at delivery (`delivered_at`), "not when it was placed".
**Evidence:** An order is created on 2026-03-01 and delivered on 2026-03-20. A customer asks for a refund on 2026-04-10, which is 21 days after delivery and 40 days after placement. `now - created_at` is 40 days, which is more than `REFUND_WINDOW`, so `is_refundable` returns `False`. The policy requires `True`. The same error rejects the exact 30-days-after-delivery case that the policy says is still accepted. Delivery never precedes placement, so the error only wrongly rejects refunds; it never wrongly grants one. Verification read `shop/orders.py` (`delivered_at` is `Optional[datetime]`, and the code has already ruled out `None` at line 10), the only caller (the new tests) and the policy. Nothing makes the scenario impossible.
**Confidence:** High
**Fix:** Use `now - order.delivered_at <= REFUND_WINDOW`.

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:15-17`
**Issue:** The only positive test cannot tell a window measured from delivery from one measured from placement, and no test covers the 30-day boundary or an expired window.
**Evidence:** In `test_refund_on_the_next_day_is_accepted`, delivery is one day after creation and `now` is one day after delivery. Both anchors give `True`, so the test passes with the bug at `shop/refunds.py:12`. No test checks exactly 30 days after delivery (accepted) or 30 days and 1 second after delivery (rejected).
**Confidence:** High
**Fix:** Add tests with delivery well after placement: one with `now` exactly 30 days after `delivered_at` (expects `True`), one just beyond it (expects `False`), and one where `now` is more than 30 days after `created_at` but within 30 days of delivery (expects `True`).

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
**Relevant tests:** changed — `tests/test_refunds.py` covers an undelivered order (`False`) and a refund one day after delivery (`True`). It leaves out the 30-day boundary, an expired window and an order delivered long after it was placed. Execution: not run.
**Look first:** `shop/refunds.py` (the window is measured from `created_at`, not `delivered_at`), `tests/test_refunds.py` (the positive test passes with the bug).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:stacks/python.md`, `tests/test_orders.py`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
