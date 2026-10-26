**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject orders whose quantity is below 1 with an HTTP 400 before anything is saved or reserved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The quantity check is the first statement in `placeOrder`, inside the existing `@Transactional` method. A rejected request writes nothing, and the "both happen or neither does" contract in the Javadoc still holds. The Javadoc was updated to match.
- `InvalidQuantityException` uses `@ResponseStatus(HttpStatus.BAD_REQUEST)`, so a bad quantity from `OrderController.create` returns 400. Before, it would have reached `orders.save` and `stock.reserve`. The exception message includes the rejected value and no internal detail.
- Moving the persistence work into the private `persist` method keeps `placeOrder` short. `persist` is called from inside the transactional `placeOrder`, so the self-call does not bypass the transaction proxy.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:19-21`
**Issue:** The new `quantity < 1` validation and the new `InvalidQuantityException` have no test.
**Evidence:** A later edit turns the guard into `quantity < 0` or `quantity == 0`, or drops it. A request such as `{"sku":"A","quantity":0}` then reaches `orders.save` and `stock.reserve` again, and no test fails. I found no test sources in the repository (`git ls-files` lists none, and `pom.xml` has no `spring-boot-starter-test`), so none runs this path.
**Confidence:** High
**Fix:** Add a service-level test, with the repositories mocked, for `placeOrder("A", 0)` and `placeOrder("A", -1)`. It should assert that `InvalidQuantityException` is thrown and that `orders.save` and `stock.reserve` are never called. Add a boundary case for quantity 1, and a `POST /orders` check that the status is 400.

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
**Relevant tests:** missing — I looked in the repository's tracked files (`git ls-files`) and found no test sources and no test dependency in `pom.xml`, so nothing covers `placeOrder` or the new 400 response. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (new validation branch with no test, and the changed transactional method).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, API Design, Stack-Specific.
**Not verified:** nothing.
