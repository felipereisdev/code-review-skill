**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject order requests with a quantity below 1 using a new `InvalidQuantityException` that maps to HTTP 400, before the order is saved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The check is a small guard at the top of the service method. It fails fast, before any database work.
- `InvalidQuantityException` carries `@ResponseStatus(HttpStatus.BAD_REQUEST)` and a message that includes the rejected value, so the client gets a 400 instead of a generic 500.
- The new class is minimal and follows the existing exception style (`OutOfStockException`).

## Findings

### Potential Bugs — Critical

**Location:** `src/main/java/com/example/shop/OrderService.java:17-26`
**Issue:** The change splits `placeOrder` into an unannotated public `placeOrder` that calls `persist(...)` on `this`, and moves `@Transactional` onto `persist`. Spring applies `@Transactional` through a proxy, and a call from one method to another on the same object does not go through that proxy. So `persist` never runs inside a transaction. `placeOrder` used to be `@Transactional`, so this removes the atomicity the code still promises in its comment ("both happen or neither does").
**Evidence:** `OrderController.create` calls `orders.placeOrder("SKU-1", 5)` on the proxied `OrderService` bean. `placeOrder` is not transactional, so no transaction opens. It then calls `this.persist(...)` directly, which skips the proxy and so skips the `@Transactional` advice. `orders.save(new Order(...))` commits immediately in its own transaction, because Spring Data's `save` is transactional by itself. `stock.reserve(...)` then runs in a separate transaction (`StockService.reserve` is `@Transactional`). When the stock is too low, `stock.decrement` returns 0 and `OutOfStockException` is thrown. Only the stock transaction rolls back. The already-committed order row stays, so the database holds an order with no reserved stock and the client gets a 500. Verification checked `pom.xml` (Spring Boot 3.3.4 with `spring-boot-starter-web` and `spring-boot-starter-data-jpa`, no `spring-aspects` and no AspectJ transaction mode), `OrderController` (the only caller, which goes through the proxy) and `StockService` (it has its own transaction, not an outer one). Nothing makes `persist` transactional when called from `placeOrder`.
**Confidence:** High
**Fix:** Keep one transactional entry point. Put `@Transactional` on `placeOrder` and inline the persist body. The validation throws before any database work, so it costs nothing inside the transaction. Alternatively, move `persist` into another bean so the call goes through its proxy. Do not leave a public `persist` that callers can reach without a transaction. Add a test for the rollback (see the Tests/Coverage finding).

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:17-22`
**Issue:** The new validation and the restructured transaction boundary have no tests. The repository has no `src/test` directory.
**Evidence:** `placeOrder("SKU-1", 0)` and `placeOrder("SKU-1", -3)` are expected to throw `InvalidQuantityException`, and nothing checks that. A test that makes `reserve` throw and then asserts that no `Order` row remains would have caught the transaction regression above.
**Confidence:** High
**Fix:** Add a unit test for the boundary values (0, 1, negative). Add a Spring integration test, for example with `@SpringBootTest` or `@DataJpaTest`, that checks the order is rolled back when `OutOfStockException` is thrown.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 0          |     |
| Accessibility         |          |         |            | N/A |
| Observability         |          |         |            | N/A |
| API Design            | 0        | 0       | 0          |     |
| Resilience            | 0        | 0       | 0          |     |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** missing — I looked for tests in the tracked files (`git ls-files` shows no `src/test` directory and no test files) and found none, so nothing covers `placeOrder`, the new validation or the transaction boundary. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (the Critical self-invocation finding: `@Transactional` no longer applies to the order flow), `src/main/java/com/example/shop/InvalidQuantityException.java` (new file, no findings).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/resilience.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, API Design, Resilience, Stack-Specific.
**Not verified:** nothing.
