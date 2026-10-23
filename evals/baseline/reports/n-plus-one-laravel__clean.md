# Code Review: staged changes

**Scope:** staged changes only (`git diff --cached`).
**Stack:** Laravel 11 with PHPUnit, using Blade views. I loaded `stacks/laravel.md`. No Pest, Inertia, Vue or architecture-pattern files apply.
**Files reviewed:** `OrderController.php`, `orders/index.blade.php`, `OrderIndexTest.php`.

## What Was Done Well
- `with('customer')` and `withCount('items')` remove the N+1 for the two new columns. `withCount` avoids loading item collections just to count them, as the Laravel checklist recommends.
- The controller stays short (under 10 lines) and still paginates at 25 per page.
- The view uses `{{ }}`, so output is escaped.
- The view uses `?->` for the customer, so a missing customer won't crash the page.
- The test was extended to cover the new customer column.

## Findings

### Tests/Coverage — Warning

**File:** `tests/Feature/OrderIndexTest.php:22`
**Issue:** The new `items_count` column and the `withCount('items')` call have no test. The test creates an order with no items, so a broken count wouldn't be caught.
**Fix:** Create an order with a known number of items (e.g. `OrderItem::factory()->count(3)->for($order)->create()`). Then assert that the count renders, for example with `assertSeeInOrder([$order->number, $order->customer->name, '3'])`. A bare `assertSee('3')` is too loose and can match any "3" on the page.

### Potential Bugs — Suggestion

**File:** `tests/Feature/OrderIndexTest.php:22`
**Issue:** The view tolerates a null customer (`$order->customer?->name`), but the test dereferences `$order->customer->name` directly. If `Order::factory()` doesn't create a customer, or the `customer_id` column is nullable, the test fails with a null error instead of a meaningful assertion. I couldn't check the factory or migration because they aren't in the repo snapshot. Also, no test covers an order with no customer, which the view code explicitly allows.
**Fix:** Confirm the factory sets `customer_id` (e.g. `'customer_id' => Customer::factory()`). Add a case for an order without a customer to check the page still renders.

### Accessibility — Suggestion

**File:** `resources/views/orders/index.blade.php:5-6`
**Issue:** The table has no `<thead>` or `<th>` elements, and this change adds two more unlabeled columns (customer, item count). Screen-reader users can't tell what each column means. The missing header row was already there before this diff, but the change makes it worse.
**Fix:** Add `<thead><tr><th scope="col">…</th></tr></thead>` with headers for number, customer, items and date. If the app is localized, use translation keys.

### Performance — Suggestion

**File:** `app/Http/Controllers/OrderController.php:13`
**Issue:** `with('customer')` loads every customer column, but the view only needs `name`. This is minor with 25 rows per page.
**Fix:** Optionally use `with('customer:id,name')`. Keep the `id` column, since it's the key the relationship needs.

### Performance — Suggestion

**File:** `app/Http/Controllers/OrderController.php:15`
**Issue:** `latest()` orders by `created_at`, and `withCount('items')` adds a correlated subquery. If `orders.created_at` and `order_items.order_id` aren't indexed, this slows down as the tables grow. I couldn't see the migrations to check.
**Fix:** Make sure `order_items.order_id` (a `constrained()` foreign key gives you this) and `orders.created_at` are indexed.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 2          |     |
| Tests/Coverage        | 0        | 1       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 1          |     |
| Accessibility         | 0        | 0       | 1          |     |
| Observability         | 0        | 0       | 0          | N/A |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **1**   | **4**      |     |

No blocking issues. The one Warning is the missing test for the item count.
