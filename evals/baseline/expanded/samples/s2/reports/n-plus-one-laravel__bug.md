**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show each order's customer name and item count in the orders list (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The new view cells use `{{ }}`, so customer names are HTML-escaped.
- `$order->customer?->name` is null-safe, so an order without a customer does not crash the page.
- The controller already paginates (`paginate(25)`), so the list stays bounded.
- The existing feature test was extended to assert the new customer column.

## Findings

### Performance — Warning

**Location:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The view reads `$order->customer` and `$order->items->count()` for each order, but `OrderController::index` loads neither relation. Each row lazy-loads the customer and the whole items collection.
**Evidence:** `GET /orders` with a full page of 25 orders → the loop in the view runs one `customers` query and one `order_items` query per row, about 50 extra queries on top of the 2 base queries. The count grows with page size, and `items->count()` also loads every item row just to count them. Verification read `app/Http/Controllers/OrderController.php:12-14` (no `with()` or `withCount()`) and `app/Models/Order.php` (no `$with`). Nothing else eager-loads these relations.
**Confidence:** High
**Fix:** In the controller use `Order::query()->with('customer')->withCount('items')->latest()->paginate(25)`. In the view use `$order->items_count` instead of `$order->items->count()`.

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test asserts only the customer name. It does not cover the item count, an order with no customer (the `?->` branch), or the number of queries.
**Evidence:** Replacing `$order->items->count()` with a wrong value, or breaking the null-customer path, still leaves `test_it_lists_orders` passing. A lazy-loading regression would not be caught either.
**Confidence:** High
**Fix:** Add a case with an order that has several items and assert the count. Add a case with a null customer. Optionally assert the query count or enable `Model::preventLazyLoading()` in the test.

### Accessibility — Suggestion

**Location:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The change adds two data columns to a table that has no `<thead>` or `<th>` cells.
**Evidence:** A screen-reader user reaches a row reading "1001, Alice, 3, 2026-10-26" with no column headers → they cannot tell which cell is the customer, the item count or the date.
**Confidence:** High
**Fix:** Add `<thead><tr><th scope="col">…</th></tr></thead>` that labels each column.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 1       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         | 0        | 0       | 1          |     |
| Observability         | 0        | 0       | 0          | N/A |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **1**   | **2**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `OrderIndexTest::test_it_lists_orders` now asserts that the order number and the customer name appear on `/orders`. It does not cover the item count, an order with no customer, or query counts. Execution: not run.
**Look first:** `resources/views/orders/index.blade.php` (lazy-loaded `customer` and `items` per row, the Warning), `tests/Feature/OrderIndexTest.php` (the new assertion depends on the Order factory setting a customer).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Http/Controllers/OrderController.php`, `app/Models/Customer.php`, `app/Models/Order.php`, `app/Models/OrderItem.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`, `skill:stacks/pest.md`.
**Checked with no findings:** Security, Architecture, Code & File Size, Potential Bugs, Privacy/Compliance, Stack-Specific.
**Not verified:**
- `OrderFactory` and the orders and customers migrations — context not read, not material: the repository has no `database/` directory, so I could not check that the factory sets a customer. The production change is judged without it. Only the new test line `$order->customer->name` depends on it.
