**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject order requests whose quantity is below 1 with an HTTP 400 before any order is saved or stock is reserved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The quantity check runs first in `placeOrder`, before `orders.save` and `stock.reserve`. An invalid request therefore never touches the database.
- The check sits in the `@Transactional` service method, so every caller is covered. The call to the private `persist` is a plain internal call, which stays inside the transaction `placeOrder` already opened. The "both happen or neither does" contract is kept.
- `InvalidQuantityException` carries `@ResponseStatus(HttpStatus.BAD_REQUEST)`, so a client error returns 400. The message names the rejected value and no internals.
- The Javadoc on `placeOrder` was updated to describe the new validation.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:19-21`
**Issue:** The new quantity validation has no test. The repository has no `src/test` directory at all.
**Evidence:** A later refactor of `placeOrder` drops or reorders the `quantity < 1` guard → `quantity = 0` or a negative value reaches `stock.reserve`, and nothing fails. The boundary (`0` rejected, `1` accepted) and the 400 mapping have no regression coverage.
**Confidence:** High
**Fix:** Add a test for `placeOrder` with `quantity` 0 and -1 (expects `InvalidQuantityException`, with no `save` and no `reserve`) and with 1 (succeeds). Optionally add a `POST /orders` test that expects status 400.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
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
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; public API contracts.
**Relevant tests:** missing — I looked for tests of `placeOrder` and `POST /orders` and found no `src/test` directory and no test file. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (new validation and the `persist` split, with no test), `src/main/java/com/example/shop/InvalidQuantityException.java` (new 400 contract of `POST /orders`).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, API Design, Stack-Specific.
**Not verified:** nothing.
