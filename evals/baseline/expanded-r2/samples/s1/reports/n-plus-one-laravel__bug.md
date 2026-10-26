**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show the customer name and the item count for each order in the orders list (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and does one thing.
- The new test assertion extends the existing feature test instead of adding a parallel one.
- `$order->customer?->name` uses the nullsafe operator, so an order without a customer does not crash the view.
- Output goes through `{{ }}`, which escapes it, so the customer name is safe in HTML text.
- The `/orders` route sits behind the `auth` middleware (`routes/web.php:6`).

## Findings

### Performance — Warning

**Location:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The new columns read the `customer` and `items` relations for every order in the loop. `OrderController::index` loads the orders with no `with()` or `withCount()`, so each relation is lazy-loaded once per row.
**Evidence:** `GET /orders` renders a page of 25 orders (`paginate(25)`) → `$order->customer` runs one `SELECT` per row, and `$order->items->count()` runs one more per row while loading every item model just to count them. That is up to 50 extra queries per request, and the item rows loaded grow with order size. Verification read `OrderController.php`, `Order.php` and `Customer.php`. Nothing eager-loads these relations: the query has no `with()` or `withCount()`, and `Order` has no `$with`.
**Confidence:** High
**Fix:** In `OrderController::index`, use `Order::query()->with('customer')->withCount('items')->latest()->paginate(25)`. In the view, use `$order->items_count` in place of `$order->items->count()`.

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The test checks the customer name but not the item count column. It does not cover an order with no customer, which is the case the `?->` in the view handles. It also does not guard against the query growth above.
**Evidence:** Item count → a regression in that column (for example the wrong relation or a wrong count) would still pass, because only `number` and `customer->name` are asserted. Order without a customer → the nullsafe branch is never run.
**Confidence:** High
**Fix:** Create an order with a known number of items and assert the count. Add a case for an order without a customer. Optionally assert the query count for a page of orders.

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
**Relevant tests:** changed — `OrderIndexTest::test_it_lists_orders` now asserts that the page shows the order number and the customer name. It does not cover the item count, an order without a customer, or the number of queries. Execution: not run.
**Look first:** `resources/views/orders/index.blade.php` (per-row lazy loading of `customer` and `items`), `tests/Feature/OrderIndexTest.php` (the new columns are only partly covered).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Http/Controllers/OrderController.php`, `app/Models/Customer.php`, `app/Models/Order.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Architecture, Code & File Size, Potential Bugs, Accessibility, Privacy/Compliance, Stack-Specific.
**Not verified:**
- `Order` factory and database setup — context not read, not material: the repository has no factory file, so I could not check that the factory creates a customer for the test. This does not change the N+1 finding.
- Application bootstrap or service providers, such as a `preventLazyLoading()` setting — context not read, not material: the repository has none, and the controller shows the relations are not eager-loaded.
