**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject orders with a quantity below 1 with an HTTP 400 before they are saved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The validation is a fail-fast check at the service entry point.
- `InvalidQuantityException` carries `@ResponseStatus(HttpStatus.BAD_REQUEST)` and a clear message that includes the offending value.
- Splitting validation from persistence is a reasonable idea. The problem is how it is wired (see the finding below).

## Findings

### Potential Bugs — Critical

**Location:** `src/main/java/com/example/shop/OrderService.java:17-30`
**Issue:** `placeOrder` is no longer transactional and calls `persist(...)` on `this`. Spring applies `@Transactional` through a proxy, and a call from inside the same bean never goes through it. The `@Transactional` on `persist` is therefore ignored for every order placed through `OrderController`. The saved order and the stock reservation no longer commit or roll back together, which is what the `persist` Javadoc ("both happen or neither does") promises.
**Evidence:** `POST /orders` with an SKU that has less stock than `quantity` → `OrderController.create` calls `placeOrder`, which calls `this.persist(...)` directly, so no transaction is opened there. `orders.save(...)` commits in its own transaction (the repository's own transactional `save`). `stock.reserve` then runs in its own transaction, finds `decrement` returns 0 and throws `OutOfStockException`. Nothing rolls back the already committed order, so an order row exists for stock that was never reserved. Verification checked the callers (the controller is the only one and calls `placeOrder`), the class and the bean for a class-level `@Transactional`, and `pom.xml` for AspectJ weaving (there is none, so Spring's default proxy mode applies). Nothing there makes the proxy apply to the internal call. The old code was a single `@Transactional` `placeOrder` and did not have this problem.
**Confidence:** High
**Fix:** Keep `@Transactional` on the method that the controller calls. Annotate `placeOrder` itself, with the quantity check first, and make `persist` private or inline it. Alternatively, move the check into the controller, or into a bean that calls the transactional service through the proxy. Add an integration test that forces `OutOfStockException` and asserts that no order row remains.

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:17-22`
**Issue:** The change adds validation and a new exception but no test. A test of the failure case would also have exposed the transaction regression above.
**Evidence:** `placeOrder("sku", 0)` and `placeOrder("sku", -1)` throw `InvalidQuantityException`, and `placeOrder("sku", 1)` still calls `persist`. I found no `src/test` directory, and nothing runs either path.
**Confidence:** High
**Fix:** Add tests for quantity 0, a negative quantity and the boundary of 1 (the 400 status via MockMvc). Add the rollback test described above.

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
| Observability         | 0        | 0       | 0          |     |
| API Design            | 0        | 0       | 0          |     |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** missing — I looked for tests under `src/test` and found none, so nothing covers `placeOrder` or `persist`. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (calls `persist` on `this`, so the `@Transactional` boundary is lost and an order can be saved without its stock reserved).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Observability, API Design, Stack-Specific.
**Not verified:** nothing.
