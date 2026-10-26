**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject orders with a quantity below 1 with a 400 response before they are saved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `InvalidQuantityException` carries `@ResponseStatus(BAD_REQUEST)`, so a bad quantity becomes a 400 instead of a 500.
- The exception message includes the offending value.
- The validation sits in the service layer, so it applies to every caller of `placeOrder`.

## Findings

### Potential Bugs — Critical

**Location:** `src/main/java/com/example/shop/OrderService.java:17-30`
**Issue:** `placeOrder` now calls `persist(...)` on `this`. Spring applies `@Transactional` through a proxy, and a call from inside the same object skips the proxy. `persist` therefore runs without the transaction that "both happen or neither does" depends on. The old code had `@Transactional` on the method the controller called, so the boundary worked.
**Evidence:** `POST /orders` with a sku that has no stock → `OrderController.create` calls `placeOrder` through the proxy, which has no transaction → `persist` runs as a plain `this` call, so `orders.save(...)` commits in its own repository transaction. `StockService.reserve` then runs in its own transaction, `stock.decrement` returns 0 and `OutOfStockException` is thrown. Nothing rolls back the committed order row, so the client gets an error and the database keeps an order with no stock reserved. Verification checked the project setup: `pom.xml` has only `spring-boot-starter-web` and `spring-boot-starter-data-jpa`, with no AspectJ weaving, so default proxy-based transactions apply. It also checked the one caller, `OrderController`, which goes through `placeOrder`, and `StockService.reserve`, which only has its own transaction.
**Confidence:** High
**Fix:** Keep `@Transactional` on the method callers invoke. Annotate `placeOrder` and inline the `persist` body, which also keeps the validation inside the transaction. If `persist` must stay separate, make it private and drop its annotation. If it must remain a transactional entry point, call it through another bean, not through `this`.

### Architecture — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:24-26`
**Issue:** `persist` is public, so another bean can call it directly and skip the quantity check. Its Javadoc, "both happen or neither does", is also wrong while the call goes through `this`.
**Evidence:** A future caller invokes `orderService.persist("sku", 0)` → no `InvalidQuantityException`, and an order with quantity 0 is saved and reserved.
**Confidence:** High
**Fix:** Merge `persist` back into `placeOrder`, or make it private.

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:17-22`
**Issue:** The change adds no test for the new validation, for the boundary quantities 0 and 1, or for the rollback guarantee. A rollback test would have caught the proxy bypass.
**Evidence:** The repository has no test sources. A regression in `quantity < 1` or in the transaction boundary goes unnoticed.
**Confidence:** High
**Fix:** Add a service test for `quantity` of 0, -1 and 1. Add an integration test where `reserve` throws `OutOfStockException` and no `orders` row remains.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 1          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 0          |     |
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
| **Total**             | **1**    | **0**   | **2**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** missing — looked for test sources in `git ls-files` and the working tree and found none, so nothing covers `placeOrder`, `persist` or the new exception. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (the self-invocation of `persist` drops the transaction), `src/main/java/com/example/shop/InvalidQuantityException.java` (new 400 response contract).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/resilience.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/Order.java`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/StockRepository.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Code & File Size, API Design, Stack-Specific.
**Not verified:** nothing.
