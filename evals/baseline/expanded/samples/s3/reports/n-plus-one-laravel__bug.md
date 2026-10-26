## Intent

**Intent:** inferred: show each order's customer name and item count in the orders list, and assert the customer name in the feature test (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

**Scope:** staged (git diff --cached)

## What Was Done Well

- `$order->customer?->name` uses the nullsafe operator, so an order without a customer does not break the page.
- The existing feature test was extended to cover the new customer column.
- The list is paginated (`paginate(25)`), so the page size is bounded.

## Findings

### Performance — Warning

**Location:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The view reads the `customer` relation and counts `items` for every order, but `OrderController::index` loads neither. That is an N+1 query pattern on the orders list route.
**Evidence:** `GET /orders` loads 25 orders with one query → on each loop iteration `$order->customer` runs a `customers` query and `$order->items->count()` loads the whole `items` collection → about 51 queries per page, and every item row is loaded just to count it. The controller (`app/Http/Controllers/OrderController.php:12-14`) has no `with()` or `withCount()`, `Order` has no `$with` (`app/Models/Order.php`), and the repository has no `preventLazyLoading()` setup. The only test creates one order, so it would not show the extra queries.
**Confidence:** High
**Fix:** Load the data in the controller query: `Order::query()->with('customer')->withCount('items')->latest()->paginate(25)`. Then render `{{ $order->items_count }}` in the view.

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test checks the customer name but not the new item-count column. It creates a single order with no items and no query-count assertion.
**Evidence:** Item-count rendering changes (for example the `items_count` fix above) → no test fails. A list with several orders and items, which would expose the N+1 pattern, is never exercised.
**Confidence:** High
**Fix:** Create an order with a known number of items, assert that count appears, and optionally assert the number of queries for several orders.

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

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `OrderIndexTest::test_it_lists_orders` renders `/orders` for an authenticated user and asserts the order number and customer name; it does not cover the item count, an order without a customer, or the number of queries. Execution: not run.
**Look first:** `resources/views/orders/index.blade.php` (per-row `customer` and `items` lazy loads), `tests/Feature/OrderIndexTest.php` (the item count is not asserted).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Http/Controllers/OrderController.php`, `app/Models/Customer.php`, `app/Models/Order.php`, `app/Models/OrderItem.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Architecture, Code & File Size, Potential Bugs, Accessibility, Privacy/Compliance, Stack-Specific.
**Not verified:**
- `Order::factory()` in the test — context not read, not material: the repository has no factory files, so I could not check whether the factory creates a customer for `$order->customer->name`. Every changed behavior could be judged without it.
