**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show the customer name and item count for each order on the orders list, loading both with eager loading (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `with('customer')` and `withCount('items')` load the customer and the item count in the same query that fetches the page. The list stays at a fixed number of queries per page and does not grow with the 25 rows. This follows the Laravel checklist's `withCount()` guidance.
- The view reads `items_count` from the aggregate and does not call `$order->items->count()`. The null-safe `$order->customer?->name` avoids a crash on an order with no customer.
- The existing feature test was extended to assert the new customer column. The route is behind the `auth` middleware, and Blade `{{ }}` escapes the output.

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test covers the customer name only. It does not assert the new `items_count` column, and it does not cover an order without a customer, which the view's `?->` allows.
**Evidence:** `OrderController::index` stops calling `withCount('items')` or the view stops printing `items_count` → the test still passes, because only `number` and `customer->name` are asserted. The `customer?->name` fallback has no test either.
**Confidence:** High
**Fix:** Create the order with a known number of items (`OrderItem::factory()->count(3)`) and assert that count. Add a case for an order without a customer that asserts a 200 response.

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
**Relevant tests:** changed — `tests/Feature/OrderIndexTest.php::test_it_lists_orders` requests `/orders` as an authenticated user and asserts the order number and the customer name; it does not cover `items_count` or an order without a customer. Execution: not run.
**Look first:** `resources/views/orders/index.blade.php` (shows customer names, which are personal data, in the list), `tests/Feature/OrderIndexTest.php` (the new columns are only partly asserted).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 3 of 3 changed files: `app/Http/Controllers/OrderController.php`, `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Models/Customer.php`, `app/Models/Order.php`, `app/Models/OrderItem.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
