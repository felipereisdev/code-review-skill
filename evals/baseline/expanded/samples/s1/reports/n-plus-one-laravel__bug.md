## Intent

**Scope:** staged (git diff --cached)

**Intent:** inferred: show each order's customer name and item count in the orders list, and assert the customer name in the feature test (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The null-safe `$order->customer?->name` keeps the page from crashing when an order has no customer.
- The existing feature test was extended in the same change to cover the new customer column.
- Both new cells use Blade `{{ }}`, so the output is escaped.
- The controller already paginates (`paginate(25)`), so the list cannot grow without limit.

## Findings

### Performance — Warning

**Location:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The view lazy-loads `customer` and `items` once per order row. `OrderController::index` builds the query with no `with()` or `withCount()`.
**Evidence:** `GET /orders` returns a page of 25 orders → `$order->customer` runs one `customers` query per row, and `$order->items->count()` loads every `OrderItem` model of the order with one query per row. That is up to 50 extra queries per request, plus all item rows hydrated only to be counted. The cost grows with orders per page and with items per order. Verification checked the only caller (`app/Http/Controllers/OrderController.php:12-14`), the `Order` model (`app/Models/Order.php`, no `$with` property) and the repository. None eager-loads either relation, and the repository has no `preventLazyLoading` setup.
**Confidence:** High
**Fix:** In the controller query, add `->with('customer')->withCount('items')`. In the view, use `$order->items_count` instead of `$order->items->count()`.

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test asserts only the customer name. It does not cover the item count column or an order without a customer. Nothing in it would catch the lazy-loading problem above.
**Evidence:** Removing the `items->count()` cell, or rendering a wrong count, leaves `test_it_lists_orders` green because only `$order->number` and `$order->customer->name` are asserted. An order with `customer` null, the case the `?->` was added for, is never exercised.
**Confidence:** High
**Fix:** Add assertions for the item count with an order that has known items. Add a case with no customer. Optionally add a query-count assertion, or `Model::preventLazyLoading()` in the test setup.

### Accessibility — Suggestion

**Location:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The change grows the table from two to four data columns, and the table has no `<thead>` or `<th>` header cells.
**Evidence:** A screen-reader user moves through a row and hears a customer name and a bare number with nothing to say which is the customer, the item count or the date → they cannot tell the columns apart.
**Confidence:** High
**Fix:** Add a `<thead>` with `<th scope="col">` cells (order number, customer, items, date).

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
| Observability         |          |         |            | N/A |
| API Design            |          |         |            | N/A |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **1**   | **2**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `tests/Feature/OrderIndexTest.php::test_it_lists_orders` now also asserts the customer name on `GET /orders`; it leaves out the item count, an order with no customer, and query counts. Execution: not run.
**Look first:** `resources/views/orders/index.blade.php` (per-row lazy loading of `customer` and `items`), `tests/Feature/OrderIndexTest.php` (no coverage of the item count or a null customer).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Http/Controllers/OrderController.php`, `app/Models/Customer.php`, `app/Models/Order.php`, `app/Models/OrderItem.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Architecture, Code & File Size, Potential Bugs, Privacy/Compliance, Stack-Specific.
**Not verified:**
- `Order::factory()` and the factory's customer setup — context not read, not material: the repository has no `database/factories` files, so whether the test's order always has a customer was not checked. Every changed behavior in the view could still be judged.
