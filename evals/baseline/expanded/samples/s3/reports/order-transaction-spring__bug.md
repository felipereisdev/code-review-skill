**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject order requests with a quantity below 1 with an HTTP 400 before any order is saved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The quantity check runs before any database work, so a bad request cannot touch the order or stock tables.
- `InvalidQuantityException` has a clear message and `@ResponseStatus(HttpStatus.BAD_REQUEST)`, so the controller needs no extra handling to return a 400.
- The Javadoc on `placeOrder` and `persist` says what each method does.

## Findings

### Potential Bugs — Critical

**Location:** `src/main/java/com/example/shop/OrderService.java:17-26`
**Issue:** `@Transactional` was moved from `placeOrder` to `persist`, but `placeOrder` now calls `persist` on `this`. Spring applies `@Transactional` through a proxy, and a call from inside the same class never goes through the proxy. So `persist` runs with no transaction, and the "both happen or neither does" guarantee in its Javadoc no longer holds.
**Evidence:** `POST /orders` with a valid quantity but a SKU that has no stock → `OrderController.create` calls `placeOrder` through the proxy, which has no `@Transactional` now → `persist(sku, quantity)` is a plain `this` call, so no transaction is opened → `orders.save(...)` commits in its own repository transaction → `stock.reserve` throws `OutOfStockException`, because `decrement` updated 0 rows (`StockRepository.java:10-11`) → nothing rolls back the already-committed order row, and the client gets an error. The database is left with an order that has no reserved stock.
Verification checked the only caller (`OrderController.java:20`), `StockService.reserve`, both repositories and `pom.xml`. Spring Boot 3.3.4 uses the default proxy-based transaction advice, and nothing in the repository switches to AspectJ weaving or changes the advice mode. No test covers this path.
**Confidence:** High
**Fix:** Put `@Transactional` back on `placeOrder` and keep the quantity check inside it, before the save, so the validation still fails before any write. Drop the `persist` split, or move `persist` into a separate bean that `OrderService` calls through its proxy.

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:17-22`
**Issue:** The new validation path and the `placeOrder` and `persist` split have no tests.
**Evidence:** `quantity = 0` or `-5` → `InvalidQuantityException` and a 400 response. Nothing asserts that, and nothing asserts that a failed reservation rolls back the order. A test of the second case would have caught the lost transaction above.
**Confidence:** High
**Fix:** Add a unit test for `quantity < 1`. Add an integration test for an out-of-stock SKU that checks no order row remains.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 0          |     |
| Accessibility         | 0        | 0       | 0          | N/A |
| Observability         | 0        | 0       | 0          | N/A |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          |     |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; public API contracts.
**Relevant tests:** missing — I looked for tests of `OrderService` and the controller and the repository has no test sources, so nothing covers the validation or the transaction boundary. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (the Critical finding: `persist` is called from inside the class, so `@Transactional` does not apply), `src/main/java/com/example/shop/InvalidQuantityException.java` (new 400 response for `POST /orders`).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/intent.md`, `skill:references/resilience.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/Order.java`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OrderRepository.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockItem.java`, `src/main/java/com/example/shop/StockRepository.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Resilience, Stack-Specific.
**Not verified:** nothing.
