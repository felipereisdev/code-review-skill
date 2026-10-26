**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject `placeOrder` calls with a quantity below 1 by throwing a new `InvalidQuantityException`, which maps to HTTP 400 (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The quantity check runs at the top of `placeOrder`, before `orders.save` and `stock.reserve`. A bad request therefore never touches the database or the stock counter.
- `persist` is private and is only called from inside the `@Transactional` method. The transaction boundary and the "both happen or neither does" guarantee are unchanged, and there is no proxy self-invocation problem.
- `InvalidQuantityException` carries `@ResponseStatus(HttpStatus.BAD_REQUEST)`, so invalid input produces a 400 instead of the 500 that an unmapped exception would give. The message includes the offending value.
- The Javadoc on `placeOrder` was updated to describe the new validation step.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:19-21`
**Issue:** The new `quantity < 1` guard and the new `InvalidQuantityException` have no test.
**Evidence:** `placeOrder(sku, 0)` or `placeOrder(sku, -5)` should throw `InvalidQuantityException` (400) without saving an order or decrementing stock. Nothing pins this down, so a later edit that moves the check below `orders.save`, or changes `< 1` to `< 0`, would let `quantity == 0` through with no failing test. Verification: I listed the tracked files with `git ls-files` and found no test source under `src/test` and no test dependency in `pom.xml`.
**Confidence:** High
**Fix:** Add a unit test for `OrderService.placeOrder` covering `0`, a negative value and `1` (the boundary). It should assert that the first two throw `InvalidQuantityException` and that `OrderRepository` and `StockService` are never called. Optionally add a `@WebMvcTest` that checks `POST /orders` returns 400.

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
**Relevant tests:** missing — I looked for tests of `placeOrder` and the new exception in the tracked files (`git ls-files`) and found none; no `src/test` directory exists. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (new validation guard and the `persist` split, with no test), `src/main/java/com/example/shop/InvalidQuantityException.java` (new exception that fixes the HTTP 400 mapping for `POST /orders`).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, API Design, Stack-Specific.
**Not verified:** nothing.
