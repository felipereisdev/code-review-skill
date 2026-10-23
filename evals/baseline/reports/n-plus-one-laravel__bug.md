# Code Review: staged changes (`git diff --cached`)

**Stack detected:** Laravel 11 (PHP 8.2) with PHPUnit and Blade views. I loaded `stacks/laravel.md`. I found no Vue, Inertia, Pest or architecture-pattern signals, so none of those apply.

**Files reviewed:**
- `resources/views/orders/index.blade.php`
- `tests/Feature/OrderIndexTest.php`

I also read `OrderController` and the `Order` model to trace the data path.

## What Was Done Well
- The change is small and focused: two new columns in the view, plus a test assertion for the new customer column.
- `$order->customer?->name` uses the nullsafe operator, so an order without a customer won't crash the page.
- The controller already paginates (25 per page), which bounds the cost of the issues below.
- The existing test was extended instead of a new one being added, which matches the project's conventions.

## Findings

### Performance — Warning (N+1 queries)

**File:** `resources/views/orders/index.blade.php:5-6`
**Issue:** `OrderController::index()` (`app/Http/Controllers/OrderController.php`) queries `Order::query()->latest()->paginate(25)` with no eager loading. The view now reads `$order->customer` and `$order->items` for each row. That adds up to 25 customer queries and 25 item queries per page, on top of the base queries. `$order->items->count()` also loads every `OrderItem` model just to count them. Neither the page nor the test will show this, because the test creates a single order and the project does not enable `Model::preventLazyLoading()`.
**Fix:** Eager-load the customer and aggregate the item count in SQL, in the controller:
```php
$orders = Order::query()
    ->with('customer:id,name')
    ->withCount('items')
    ->latest()
    ->paginate(25);
```
Then use `{{ $order->items_count }}` in the view. This follows the Laravel checklist rule on `withCount()` for aggregates. Consider enabling `Model::preventLazyLoading(! app()->isProduction())` in `AppServiceProvider` so regressions like this fail in development.

### Tests/Coverage — Warning

**File:** `tests/Feature/OrderIndexTest.php:21-22`
**Issue:**
- The new items-count column has no assertion.
- The null-customer path is not tested, even though the view's `?->` suggests customers can be null.
- The test has a single order, so it cannot catch the N+1 above or any per-row issue.
- `assertSee($order->customer->name)` would throw a null dereference if the factory ever produced an order without a customer.

**Fix:** Create the order with known items, for example `Order::factory()->hasItems(3)->create()`, and assert the count renders. Add a second test with an order whose `customer_id` is null and assert the page returns 200. Optionally create several orders and assert the query count stays constant, for example with `DB::enableQueryLog()` or `assertQueryCount`. Also pin the customer name in the factory so `assertSee` does not depend on random data or HTML escaping. A name like `O'Brien` would render as `O&#039;Brien`, and `assertSee` escapes by default, so check that it behaves as expected.

### Accessibility — Suggestion

**File:** `resources/views/orders/index.blade.php:1-9`
**Issue:** The table has no `<thead>` or `<th>` header cells, so the two new columns (customer and item count) have no accessible labels. This predates the diff, but each added column makes the table harder for screen-reader users to navigate.
**Fix:** Add `<thead><tr><th scope="col">…</th></tr></thead>` with headings for each column. If the project uses translation helpers, use those for the header text.

### Potential Bugs — Suggestion

**File:** `resources/views/orders/index.blade.php:5`
**Issue:** When an order has no customer, the cell renders empty with no placeholder, so it is ambiguous whether data is missing or the column is broken.
**Fix:** Use a fallback, for example `{{ $order->customer?->name ?? '—' }}`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 1       | 0          |     |
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
| **Total**             | **0**    | **2**   | **2**      |     |

The Laravel-specific checks (`withCount()`, `preventLazyLoading`) are reported under Performance. Blade output uses `{{ }}`, so it is escaped and there is no XSS issue.

**Verdict:** No blockers. The N+1 is bounded by pagination, but fixing it in the controller is a small change and best done in the same PR.
