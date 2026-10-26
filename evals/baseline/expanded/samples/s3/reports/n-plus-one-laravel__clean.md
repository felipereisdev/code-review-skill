**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show the customer name and item count for each order on the orders list, loading both without extra per-row queries (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `with('customer')` and `withCount('items')` load both new columns in one query each, so the 25 rows on a page don't cause N+1 queries. `withCount` is the aggregate helper the Laravel checklist recommends.
- The view uses `$order->customer?->name`, so an order without a customer doesn't throw.
- The existing feature test was extended to cover the new customer column.
- The route stays behind the `auth` middleware, and every new value is printed with Blade `{{ }}`, which escapes it.

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test checks only the customer name. It doesn't check `items_count`, and it doesn't cover an order with no customer, which the view's `?->` allows.
**Evidence:** Someone removes `->withCount('items')` from `OrderController::index` → `$order->items_count` renders as an empty cell, and `test_it_lists_orders` still passes because it never asserts the count. The same applies to the null-customer branch: nothing exercises it.
**Confidence:** High
**Fix:** Create an order with a known number of items and assert that the count appears. Add a case for an order without a customer that asserts a 200 response.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         | 0        | 0       | 0          |     |
| Observability         |          |         |            | N/A |
| API Design            |          |         |            | N/A |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 3 files; personal data.
**Relevant tests:** changed — `tests/Feature/OrderIndexTest.php` loads `/orders` as an authenticated user and asserts the order number and the customer name. It doesn't cover `items_count` or an order without a customer. Execution: not run.
**Look first:** `tests/Feature/OrderIndexTest.php` (the new columns are only partly covered), `resources/views/orders/index.blade.php` (the view now shows the customer name, which is personal data).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 3 of 3 changed files: `app/Http/Controllers/OrderController.php`, `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Models/Customer.php`, `app/Models/Order.php`, `app/Models/OrderItem.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Privacy/Compliance, Stack-Specific.
**Not verified:**
- Order factory definition — context not read, not material: the repository has no factory files, so I couldn't check whether `Order::factory()` creates a customer. The new test line `$order->customer->name` depends on that. This doesn't affect the judgment of the changed application code.
