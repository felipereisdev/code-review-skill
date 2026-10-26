**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject order requests with a quantity below 1 by throwing `InvalidQuantityException`, mapped to HTTP 400, before the order is saved and stock is reserved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The check is the first statement of the `@Transactional` method. A bad request fails before `orders.save` and `stock.reserve`, so nothing is written.
- Moving the persistence into a private `persist` method that `placeOrder` calls keeps one transaction boundary. The "both happen or neither does" contract in the Javadoc still holds.
- `InvalidQuantityException` carries `@ResponseStatus(HttpStatus.BAD_REQUEST)`. A client error therefore comes back as 400 and not as a generic 500.
- The exception message includes the rejected value, and the class is small and focused.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:19-21`
**Issue:** The new `quantity < 1` guard and `InvalidQuantityException` have no test. The repository has no `src/test` directory, and `pom.xml` has no test dependency.
**Evidence:** A later edit changes the guard to `quantity < 0`, so `placeOrder("sku", 0)` saves an order and calls `stock.reserve(sku, 0)`. Nothing fails, and the boundary at 0 and the 400 mapping regress unnoticed.
**Confidence:** High
**Fix:** Add tests for `placeOrder` with `0` and a negative quantity. They should assert that `InvalidQuantityException` is thrown and that neither `orders.save` nor `stock.reserve` is called. Add a controller test that `POST /orders` with such a quantity returns 400.

## Pre-existing issues (not counted)

- `src/main/java/com/example/shop/OutOfStockException.java:3` — has no `@ResponseStatus` or handler, so an out-of-stock order most likely returns 500. The new `InvalidQuantityException` returns 400, so error statuses on `POST /orders` are now inconsistent.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         |          |         |            | N/A |
| Observability         | 0        | 0       | 0          |     |
| API Design            | 0        | 0       | 0          |     |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 1 refuted. The refuted candidate was a possible self-invocation transaction bypass. `persist` is private and is called from the `@Transactional` `placeOrder`, so the proxy's transaction already covers it.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; public API contracts.
**Relevant tests:** missing — I looked for tests of `OrderService.placeOrder` and `OrderController.create` and found no `src/test` directory and no test dependency in `pom.xml`. Nothing covers the new validation or the 400 response. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (new quantity guard and the `persist` extraction, with no tests), `src/main/java/com/example/shop/InvalidQuantityException.java` (new 400 mapping on the `POST /orders` path).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Observability, API Design, Stack-Specific.
**Not verified:** nothing.
