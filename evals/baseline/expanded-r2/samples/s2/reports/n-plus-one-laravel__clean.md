**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show each order's customer name and item count on the orders list, loading both with the page's query (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The controller loads `customer` with `with('customer')` and counts items with `withCount('items')` in the same query. The list page therefore avoids an N+1 query per row, and no collection is loaded just to count it (`app/Http/Controllers/OrderController.php:13-14`).
- The view reads `$order->items_count`, the alias `withCount` produces, so the controller and view agree on the name.
- The view uses the null-safe `$order->customer?->name`, so an order with no customer does not crash the page.
- The existing test was extended in the same change to cover the new customer column. The route is already behind `auth` middleware (`routes/web.php:6`).

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test checks only the new customer-name column. It does not check the new items-count column or the null-customer path that the view's `?->` guards.
**Evidence:** `$order->items_count` is changed to `$order->items->count()`, or `withCount('items')` is dropped from the controller → the page still renders, no assertion fails, and the item-count column goes wrong without the test noticing. A null `customer` is likewise not exercised.
**Confidence:** High
**Fix:** Create an order with a known number of `OrderItem` rows and assert the count appears. Add a case for an order with no customer, if `customer_id` is nullable.

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
| API Design            | 0        | 0       | 0          |     |
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
**Relevant tests:** changed — `tests/Feature/OrderIndexTest.php` (`test_it_lists_orders`) now also asserts the customer name appears on `/orders`. It leaves out the items-count column and an order with no customer. Execution: not run.
**Look first:** `app/Http/Controllers/OrderController.php` (the new eager load and count behind both new columns), `tests/Feature/OrderIndexTest.php` (the new assertion leaves the item count uncovered).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 3 of 3 changed files: `app/Http/Controllers/OrderController.php`, `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Models/Customer.php`, `app/Models/Order.php`, `app/Models/OrderItem.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:**
- `Order` and `Customer` factories — context not read, not material: the repository has no factory or migration files, so I could not confirm that the factory creates a customer and that `customer_id` is nullable. The controller and view behavior was judged without them.
