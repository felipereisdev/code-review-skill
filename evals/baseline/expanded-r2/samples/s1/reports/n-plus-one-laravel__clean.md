**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show each order's customer name and item count on the orders index, loading both with eager loading and a count aggregate (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The controller uses `with('customer')` and `withCount('items')`. This avoids an N+1 query on the new view columns and avoids loading item collections just to count them. It matches the Laravel stack guidance on aggregate helpers.
- The view reads `$order->customer?->name`, so an order without a customer does not crash the page.
- The existing feature test was extended to cover the new customer column.

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test asserts the new customer name but not the new `items_count` column, so the `withCount('items')` addition has no test.
**Evidence:** `withCount('items')` is removed from the controller, or the view column is dropped → `test_it_lists_orders` still passes, because it asserts only `number` and `customer->name`.
**Confidence:** High
**Fix:** Create items for the order, for example `OrderItem::factory()->count(3)->for($order)->create()`, and assert the rendered count, for example `->assertSeeInOrder([$order->number, $order->customer->name, '3'])`.

### Accessibility — Suggestion

**Location:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The change adds two more data columns to a `<table>` that has no `<thead>` or `<th>` cells. Nothing labels the customer name or the item count.
**Evidence:** A screen-reader user navigates the table → hears an unlabelled name and an unlabelled bare number such as `3` beside the order number and date. The meaning of the new columns is not announced.
**Confidence:** High
**Fix:** Add a `<thead>` with `<th scope="col">` cells for Number, Customer, Items and Date.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
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
| **Total**             | **0**    | **0**   | **2**      |     |

**Verification:** 1 Critical/Warning candidate checked, 1 refuted.
**Review effort:** 1/5 — up to 50 changed lines in 3 files; no risk area.
**Relevant tests:** changed — `tests/Feature/OrderIndexTest.php::test_it_lists_orders` now asserts the order number and customer name on `GET /orders`; it does not assert `items_count`. Execution: not run.
**Look first:** `tests/Feature/OrderIndexTest.php` (the new `items_count` column is untested), `resources/views/orders/index.blade.php` (the new columns have no headers).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 3 of 3 changed files: `app/Http/Controllers/OrderController.php`, `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Models/Customer.php`, `app/Models/Order.php`, `app/Models/OrderItem.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Privacy/Compliance, Stack-Specific.
**Not verified:**
- Order factory and database schema — context not read, not material: the repository has no `OrderFactory` and no migrations. The test's `$order->customer->name` assertion depends on the factory creating a customer, and the controller and view behavior was judged without either.
