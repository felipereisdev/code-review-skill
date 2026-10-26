**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show the customer name and the item count on the orders list, loading both in the controller query (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `OrderController::index` loads `customer` with `with()` and the item count with `withCount('items')`. The list stays at a fixed number of queries per page, and the 25-row `paginate()` is kept. This follows the Laravel checklist's advice to use aggregate helpers rather than load collections (`app/Http/Controllers/OrderController.php:12-16`).
- The view uses the null-safe `$order->customer?->name`, so an order without a customer renders a blank cell instead of throwing.
- Both new values are printed with `{{ }}`, so Blade escapes them.
- The feature test was extended to cover the new customer column.

## Findings

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:** The change adds an `items_count` column and a `withCount('items')` call, but the test never asserts the count. The test also creates an order that has no items.
**Evidence:** Someone removes `->withCount('items')` or the `<td>{{ $order->items_count }}</td>` cell → `test_it_lists_orders` still passes, because it asserts only the order number and the customer name. The regression goes unnoticed.
**Confidence:** High
**Fix:** Create an order with a known number of items, for example 3, and assert that the list shows that count.

## Needs human verification

### Tests/Coverage — Warning

**Location:** `tests/Feature/OrderIndexTest.php:22`
**Issue:** `->assertSee($order->customer->name)` dereferences `customer` without a null guard. The view uses `$order->customer?->name`, which suggests that an order may have no customer.
**Evidence:** `Order::factory()->create()` produces an order with a null `customer_id` → `$order->customer` is `null`, and reading `->name` throws an `ErrorException` ("Attempt to read property on null"). `test_it_lists_orders` then errors, even though the application code is correct. A person must check whether the order factory always creates a customer. The repository has no `database/factories` directory, so I could not trace it.
**Confidence:** Medium
**Fix:** Create the order with an explicit customer, for example `Order::factory()->for(Customer::factory())->create()`, or guard the assertion for the null case.

## Pre-existing issues (not counted)

- `routes/web.php:6` — `/orders` is protected only by the `auth` middleware, and `OrderController::index` has no policy or authorization check. Any logged-in user can list every order, and the list now also shows customer names.

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

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 3 files; personal data.
**Relevant tests:** changed — `tests/Feature/OrderIndexTest.php::test_it_lists_orders` now also asserts that the customer name appears. It does not assert `items_count`, an order without a customer, or pagination. Execution: not run.
**Look first:** `tests/Feature/OrderIndexTest.php` (unguarded `$order->customer->name`, no `items_count` assertion), `resources/views/orders/index.blade.php` (shows the customer name, which is personal data), `app/Http/Controllers/OrderController.php` (new eager load and count).
**Ready to merge:** With fixes — a person must check 1 finding under Needs human verification before merging.

## Audit

**Files reviewed:** 3 of 3 changed files: `app/Http/Controllers/OrderController.php`, `resources/views/orders/index.blade.php`, `tests/Feature/OrderIndexTest.php`.
**Read for context:** `app/Models/Customer.php`, `app/Models/Order.php`, `app/Models/OrderItem.php`, `composer.json`, `routes/web.php`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Privacy/Compliance, Stack-Specific.
**Not verified:**
- Order factory — context not read, not material: the repository has no `database/factories` directory, so I could not tell whether `Order::factory()` sets a customer. The controller and view behavior were fully judged without it.
