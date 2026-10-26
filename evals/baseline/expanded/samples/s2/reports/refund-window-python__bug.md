## Scope

**Scope:** staged (git diff --cached)

## Intent

**Intent:** Implement the refund rule of `policy/refund-policy.md` as `is_refundable(order, now)` (request, `policy/refund-policy.md`).
**Requirements:** 1 met, 2 not met, 0 not judged.
- Not met — the 30-day window starts at delivery (`Order.delivered_at`), not at placement, and a request exactly 30 days after delivery is accepted (`policy/refund-policy.md`): `shop/refunds.py:12` measures `now - order.created_at`. The `<=` boundary is correct, but the window starts at the wrong date.
- Met — an undelivered order (`delivered_at is None`) is not refundable through `is_refundable` (`policy/refund-policy.md`): `shop/refunds.py:10-11` returns `False` in that case.
- Not met — `is_refundable(order, now)` returns `True` when a refund can be granted and `False` otherwise (`policy/refund-policy.md`): `shop/refunds.py:12` returns `False` for a delivered order that is still inside 30 days of delivery but more than 30 days after placement.
**Scope creep:** none found in the reviewed files.
**Sources not read:** none.

## What Was Done Well

- `is_refundable` is a small pure function. `now` is passed in, so the logic is deterministic and easy to test.
- The window is a named constant (`REFUND_WINDOW`), and the `<=` comparison already makes the 30-day boundary inclusive.
- The undelivered case is a clear early return, and the docstring points to the policy file.
- The change adds tests alongside the code.

## Findings

### Potential Bugs — Warning

**Location:** `shop/refunds.py:12`
**Issue:** The refund window is measured from `order.created_at`, but the policy says it starts at delivery (`Order.delivered_at`, rule 1). `created_at` is never later than `delivered_at`, so the check only ever rejects refunds it should accept.
**Evidence:** An order is placed on 2026-03-01 and delivered on 2026-03-30. A refund is requested on 2026-04-15, 16 days after delivery and 45 days after placement. `now - order.created_at` is 45 days, which is more than 30, so `is_refundable` returns `False`. The policy says the window runs from delivery, so the refund should be accepted. The same happens for any order that takes more than a day to deliver and is refunded near the end of the window. Verification read `shop/orders.py`, where `delivered_at` is `Optional[datetime]` and is not `None` at this point, and checked for callers. Nothing else in the repository calls `is_refundable`, so no guard or caller changes the result.
**Confidence:** High
**Fix:** Measure from delivery: `return now - order.delivered_at <= REFUND_WINDOW`. The `None` check above already guarantees that `delivered_at` is set.

### Tests/Coverage — Suggestion

**Location:** `tests/test_refunds.py:15-17`
**Issue:** The only test of the delivered case uses a request one day after delivery, so it passes whether the window starts at `created_at` or at `delivered_at`. Nothing tests the inclusive boundary of rule 1 ("exactly 30 days after delivery is still accepted") or a refusal after the window.
**Evidence:** Changing `shop/refunds.py:12` to the wrong anchor, or to `<` instead of `<=`, leaves both tests green, which is how the Warning above gets through.
**Confidence:** High
**Fix:** Add a case delivered more than 30 days after placement and refunded within 30 days of delivery (expects `True`). Add a case exactly 30 days after delivery (`True`). Add a case 30 days plus a moment after delivery (`False`).

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
**Relevant tests:** changed — `tests/test_refunds.py` covers an undelivered order (`False`) and a refund one day after delivery (`True`). It does not cover the 30-day boundary, a refusal after the window, or an order delivered long after it was placed. Execution: not run.
**Look first:** `shop/refunds.py` (the window starts at `created_at` instead of `delivered_at`), `tests/test_refunds.py` (no boundary or delivery-anchored case).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `shop/refunds.py`, `tests/test_refunds.py`.
**Read for context:** `policy/refund-policy.md`, `pyproject.toml`, `shop/orders.py`, `skill:references/intent.md`, `skill:stacks/python.md`, `tests/test_orders.py`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
