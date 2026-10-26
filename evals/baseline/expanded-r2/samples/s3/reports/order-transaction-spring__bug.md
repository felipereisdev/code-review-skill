**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject order requests with a quantity below 1 before the order is saved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The validation runs before any database work, and `InvalidQuantityException` carries a clear message that includes the rejected value.
- `@ResponseStatus(HttpStatus.BAD_REQUEST)` makes bad input return a 400 instead of a 500.
- The new exception follows the existing `OutOfStockException` style: an unchecked exception with a message that names the offending value.

## Findings

### Potential Bugs — Critical

**Location:** `src/main/java/com/example/shop/OrderService.java:21-26`
**Issue:** `placeOrder` is no longer `@Transactional`. It calls `this.persist(...)`, and `@Transactional` now sits only on `persist`. Spring applies it through a proxy, and a call from one method to another on the same object does not go through the proxy, so the annotation has no effect there. `persist` therefore runs with no surrounding transaction, even though its Javadoc says "both happen or neither does".
**Evidence:** `POST /orders` with a `sku` whose stock is lower than `quantity` → `OrderController.create` calls `orders.placeOrder` (`OrderController.java:20`) → `persist` runs as a plain `this.` call, so there is no transaction → `orders.save(...)` commits the order on its own → `stock.reserve(...)` throws `OutOfStockException` because `decrement` updates 0 rows (`StockService.java:16-20`) → nothing rolls back the saved order. The database keeps an order with no stock reserved, and the client gets a 500. Before this change, `@Transactional` on `placeOrder` made both steps roll back together. I checked the only caller (`OrderController`), `StockService`, and `pom.xml` (Spring Boot 3.3.4, default proxy-based transactions, no AspectJ weaving configured). Nothing else supplies a transaction around the call.
**Confidence:** High
**Fix:** Put `@Transactional` back on `placeOrder` and keep the `quantity < 1` check at the top. The check throws before any database work, so the transaction costs nothing there. Then inline `persist` or make it `private`. A public `persist` also lets any injected caller skip the validation. If a separate transactional method is wanted, move it to another bean, or use `TransactionTemplate`, so the call goes through the proxy.

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:17-22`
**Issue:** The new validation branch and its exception have no tests, and there is no test for the atomicity that `persist` promises.
**Evidence:** `placeOrder("A", 0)` and `placeOrder("A", -1)` are the boundary cases of the new `quantity < 1` check. A test that makes `reserve` throw and then asserts that no order was saved would have caught the Critical finding above. No `src/test` directory exists.
**Confidence:** High
**Fix:** Add a service test for quantity 0, -1 and 1. Add a `@SpringBootTest` or `@DataJpaTest` test where `reserve` throws `OutOfStockException` and the order count stays 0.

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
| API Design            | 0        | 0       | 0          |     |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** missing — I looked under `src/` and found no test files, so nothing covers `placeOrder`, `persist` or the new exception. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (Critical: `persist` is called from `placeOrder` on the same object, so `@Transactional` does not apply).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, API Design, Stack-Specific.
**Not verified:** nothing.
