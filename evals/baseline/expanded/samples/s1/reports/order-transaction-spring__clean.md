**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject order requests with a quantity below 1 by throwing `InvalidQuantityException`, which maps to HTTP 400, before any order is saved or stock reserved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The quantity check is the first statement of `placeOrder`, so an invalid request fails before `orders.save` or `stock.reserve` runs. No write has to be rolled back.
- `@Transactional` stays on the public `placeOrder` entry point. The new private `persist` is a plain self-call inside that same transaction, so the "both happen or neither does" contract in the Javadoc still holds. The Javadoc was updated to match.
- `InvalidQuantityException` uses `@ResponseStatus(HttpStatus.BAD_REQUEST)`, so a bad quantity from `POST /orders` becomes a 400 instead of a 500. Its message gives only the rejected number, which leaks nothing.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:19-21`
**Issue:** The new `quantity < 1` guard has no test. The repository has no test sources and no test dependency in `pom.xml`.
**Evidence:** A later edit changes the guard to `quantity < 0` or removes it → `placeOrder("sku", 0)` saves an order of 0 units and `stock.reserve` runs with 0. Nothing fails to flag the regression.
**Confidence:** High
**Fix:** Add `spring-boot-starter-test` and a unit test for `placeOrder` with `0` and a negative quantity. It should assert that `InvalidQuantityException` is thrown and that `orders.save` and `stock.reserve` are never called. A `@WebMvcTest` on `OrderController` could also assert the 400.

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
| Observability         |          |         |            | N/A |
| API Design            | 0        | 0       | 0          |     |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; public API contracts.
**Relevant tests:** missing — I looked for tests of `placeOrder` and found none: `git ls-files` lists no file under `src/test`, and `pom.xml` has no test dependency. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (new validation guard, no test), `src/main/java/com/example/shop/InvalidQuantityException.java` (new 400 mapping for `POST /orders`).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, API Design, Stack-Specific.
**Not verified:** nothing.
