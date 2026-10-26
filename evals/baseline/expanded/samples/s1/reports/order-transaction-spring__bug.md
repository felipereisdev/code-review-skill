**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: reject order requests with a quantity below 1 with an HTTP 400 before the order is saved and its stock reserved (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `InvalidQuantityException` carries `@ResponseStatus(HttpStatus.BAD_REQUEST)` and a message that includes the rejected value, so invalid quantities return 400 instead of 500.
- The validation sits in the service layer, so any caller of `placeOrder` gets the check, not only the controller.
- The `placeOrder` Javadoc and the `persist` Javadoc, which keeps the "both happen or neither does" contract, describe what each method does.

## Findings

### Potential Bugs — Critical

**Location:** `src/main/java/com/example/shop/OrderService.java:17-30`
**Issue:** The change moves `@Transactional` to the new method `persist`, and `placeOrder` now calls it with `return persist(sku, quantity)` on the same instance. Spring applies `@Transactional` through a proxy, and a call from one method of a bean to another method of the same bean never goes through that proxy. `persist` therefore runs with no transaction, and `placeOrder` itself is no longer transactional.
**Evidence:** `POST /orders` with a valid `sku` that has less stock than `quantity` → the controller calls `placeOrder` through the proxy, which has no transaction advice → `persist` is called directly on `this` → `orders.save(...)` commits in its own repository-level transaction → `stock.reserve(...)` throws `OutOfStockException` → nothing rolls back the already committed order. The database now holds an order with no reserved stock, which is the case the `persist` Javadoc ("both happen or neither does") says cannot happen. Verification checked `OrderController.create`, which is the only caller and goes through `placeOrder`. It also checked `StockService.reserve`, whose own `@Transactional` only covers its own work, and `pom.xml`, which has no AspectJ dependency. The repository has no other source file with transaction configuration, so Spring's default proxy mode applies. Before the change, `placeOrder` was the proxied method, so the rollback worked.
**Confidence:** High
**Fix:** Keep `@Transactional` on the method the controller calls. Annotate `placeOrder` and put the quantity check inside it, as in `@Transactional public Order placeOrder(...) { if (quantity < 1) throw ...; Order order = orders.save(...); stock.reserve(...); return order; }`. Throwing before any write does not change the transaction outcome. If the split must stay, move `persist` to a separate bean, or call it through an injected proxy of the service.

### Tests/Coverage — Suggestion

**Location:** `src/main/java/com/example/shop/OrderService.java:17-22`
**Issue:** The new validation and the transaction behavior of `placeOrder` have no tests. The repository has no test files.
**Evidence:** `placeOrder("sku", 0)` and `placeOrder("sku", -3)` are the boundary cases of `quantity < 1`, and nothing runs them. A rollback test, where `reserve` throws and the order must not remain saved, would have caught the finding above.
**Confidence:** High
**Fix:** Add a service test for `quantity` 0 and -1 that expects `InvalidQuantityException` and no call to `orders.save`. Add an integration test with `@SpringBootTest` where `reserve` throws `OutOfStockException` and the order table stays empty.

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
| Resilience            | 0        | 0       | 0          |     |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** missing — I looked for `*Test*.java` files and found none in the repository, so nothing covers `placeOrder`, the validation or the rollback. Execution: not run.
**Look first:** `src/main/java/com/example/shop/OrderService.java` (`@Transactional` moved to `persist`, which `placeOrder` calls on `this`, so the rollback is lost), `src/main/java/com/example/shop/InvalidQuantityException.java` (new 400 exception, no findings).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/main/java/com/example/shop/InvalidQuantityException.java`, `src/main/java/com/example/shop/OrderService.java`.
**Read for context:** `pom.xml`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/resilience.md`, `skill:stacks/java-spring.md`, `src/main/java/com/example/shop/OrderController.java`, `src/main/java/com/example/shop/OutOfStockException.java`, `src/main/java/com/example/shop/StockService.java`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Observability, API Design, Resilience, Stack-Specific.
**Not verified:** nothing.
