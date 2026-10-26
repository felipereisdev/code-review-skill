Reviewing the staged diff and writing the report now.

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show each order's customer name and item count in the orders list, and assert the customer name in the feature test (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The customer cell uses `$order->customer?->name`, so an order with no customer renders an empty cell instead of throwing.
- Output goes through Blade `{{ }}`, which escapes the customer name.
- The existing feature test was extended to cover the new customer column.

## Findings

### Performance — Warning

**Location:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The new `customer` and `items` columns read relations that the controller never eager-loads. Each row runs one query for the customer and one for the items. `$order->items->count()` also loads every `OrderItem` model just to count them.
**Evidence:** `GET /orders` paginates 25 orders (`OrderController::index`, `Order::query()->latest()->paginate(25)`) with no `with()` or `withCount()`. Rendering the page runs 2 pagination queries, 25 `customer` queries and 25 `items` queries, about 52 in total, and the count grows with the page size and with the number of items per order. Verification read `app/Http/Controllers/OrderController.php` and `app/Models/Order.php`. Neither has `with()`, `withCount()` or `$with`. The repository has no provider that changes lazy-loading behavior.
**Confidence:** High
**Fix:** In `OrderController::index`, use `Order::query()->with('customer')->withCount('items')->latest()->paginate(25)`. In the view, replace `$order->items->count()` with `$order->items_count`.

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test asserts only the customer name. It does not cover the new item count column or an order with no customer, which the `?->` in the view handles.
**Evidence:** Removing the `items->count()` cell, or breaking the null-customer case, would leave `test_it_lists_orders` green. Neither case is asserted.
**Confidence:** High
**Fix:** Create an order with a known number of items and assert the count. Add a case for an order without a customer that asserts a 200 response.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 1       | 0          |     |
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
| **Total**             | **0**    | **1**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.
**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `tests/Feature/OrderIndexTest.php::test_it_lists_orders` requests `/orders` as an authenticated user and asserts a 200 response, the order number and the customer name. It does not cover the item count, a null customer or the query count. Execution: not run.
**Look first:** `resources/views/orders/index.blade.php` (lazy-loads `customer` and `items` once per row, N+1), `tests/Feature/OrderIndexTest.php` (does not assert the item count or the null-customer case).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Http/Controllers/OrderController.php`, `app/Models/Customer.php`, `app/Models/Order.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`, `skill:stacks/pest.md`.
**Checked with no findings:** Security, Architecture, Code & File Size, Potential Bugs, Accessibility, Privacy/Compliance, Stack-Specific.
**Not verified:**
- Order and Customer factories — context not read, not material: the repository has no `database/factories` files, so what `Order::factory()` sets for the customer could not be checked. Every changed behavior could be judged without it.
