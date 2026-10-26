I've read the diff and the surrounding code, and I'm now writing the report.

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject order requests with a quantity below 1 by throwing an exception that maps to HTTP 400 (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The check runs first in `placeOrder`, before `orders.save` or `stock.reserve`, so an invalid request never touches the database.
- The `@Transactional` boundary stays on the public method. The new private `persist` is called from inside that transaction, so the "both happen or neither does" guarantee holds.
- `InvalidQuantityException` carries `@ResponseStatus(HttpStatus.BAD_REQUEST)`. A bad client request therefore returns 400 instead of a 500.
- The Javadoc was updated to describe the new validation step.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:16-22`
**Issue:** The new `quantity < 1` guard and `InvalidQuantityException` have no test.
**Evidence:** A later edit changes `quantity < 1` to `quantity < 0`, or removes the guard → `placeOrder("sku", 0)` and negative quantities pass validation, and nothing fails. Negative quantities would then go through `stock.decrement(sku, -n)` and could increase stock. The repository has no `src/test` directory and no test dependency in `pom.xml`.
**Confidence:** High
**Fix:** Add a unit test of `OrderService.placeOrder` for `0` and a negative quantity. It should assert that `InvalidQuantityException` is thrown and that neither `orders.save` nor `stock.reserve` is called. Add a boundary case for `1`.

## Pre-existing issues (not counted)

- `src/main/java/com/example/shop/StockService.java:19` — `OutOfStockException` has no `@ResponseStatus` and the repository has no `@ControllerAdvice`, so an out-of-stock order returns HTTP 500 rather than a client error.

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

**Verification:** 1 Critical/Warning candidate checked, 1 refuted. The refuted candidate was a possible bypass of `@Transactional` through the self-invoked `persist`. It does not happen: the annotated public `placeOrder` is the only entry point, and `persist` runs inside its transaction.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; public API contracts (`POST /orders` now answers 400 for quantity below 1).
**Relevant tests:** missing — I looked for tests of `OrderService.placeOrder` and found none: `git ls-files` lists no `src/test` files, and `pom.xml` has no test dependency. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (new validation guard, which has no test), `src/main/java/com/example/shop/InvalidQuantityException.java` (new exception that sets the 400 mapping).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/Order.java`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Observability, API Design, Stack-Specific.
**Not verified:** nothing.
