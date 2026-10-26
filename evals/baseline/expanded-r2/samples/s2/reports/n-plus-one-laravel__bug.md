**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show the customer name and the item count for each order on the orders list (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `$order->customer?->name` uses the null-safe operator, so an order without a customer does not crash the page.
- Blade `{{ }}` escapes the new customer name, so rendering user-supplied names is safe.
- The existing feature test was extended to cover the new customer column instead of being left as it was.

## Findings

### Performance — Warning

**Location:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The view reads `$order->customer` and `$order->items` for every order, but `OrderController::index` loads neither relation. Each row triggers one lazy-load query for the customer and one for the items.
**Evidence:** `GET /orders` renders a page of 25 orders (`paginate(25)`) → the loop runs up to 25 customer queries and 25 item queries, about 50 extra queries per request on top of the 2 pagination queries. Verification read `OrderController.php:12-14`, `Order.php:14-22` and `composer.json`. The query has no `with()` or `withCount()`, `Order` has no `$with`, and the repository has no `preventLazyLoading` setup, so nothing prevents the lazy loads. `$order->items->count()` also loads every item model only to count them.
**Confidence:** High
**Fix:** In the controller, use `Order::query()->with('customer')->withCount('items')->latest()->paginate(25)`. In the view, render `$order->items_count` instead of `$order->items->count()`.

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test checks the customer name for a single order. It does not assert the new item-count column, an order without a customer (the case `?->` handles), or the number of queries.
**Evidence:** Removing `<td>{{ $order->items->count() }}</td>` or the `?->` guard, or dropping eager loading from the controller, leaves `test_it_lists_orders` passing → regressions in the new columns go unnoticed.
**Confidence:** High
**Fix:** Create an order with a known number of items and assert it. Add a case for an order whose customer is null. Optionally assert the query count, or call `Model::preventLazyLoading()` in the test setup.

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
**Relevant tests:** changed — `OrderIndexTest::test_it_lists_orders` now asserts the customer name for one factory-created order. It does not cover the item count, a null customer or the query count. Execution: not run.
**Look first:** `resources/views/orders/index.blade.php` (N+1 queries on customer and items), `tests/Feature/OrderIndexTest.php` (new columns only partly covered).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Http/Controllers/OrderController.php`, `app/Models/Customer.php`, `app/Models/Order.php`, `app/Models/OrderItem.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Architecture, Code & File Size, Potential Bugs, Accessibility, Privacy/Compliance, Stack-Specific.
**Not verified:**
- Model factories — context not read, not material: the repository has no factory files, so I could not tell whether `Order::factory()` creates a customer, which the new `$order->customer->name` assertion needs. The view change was judged without it.
