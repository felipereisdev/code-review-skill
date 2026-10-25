**Scope:** branch origin/main (git diff origin/main...HEAD)

**Configuration:** `.code-review/config.yml` and 2 rule files from `.code-review/rules/`.

**Excluded by configuration:** 2 changed files match ignore_paths and were not reviewed: `docs/setup.md`, `src/generated/client.ts`.

### What Was Done Well

- The user and order handlers share one error type and one response shape.

## Findings

### Security — Critical

**Location:** `src/api/users.ts:14-15`
**Issue:** The handler copies `role` from the request body into the new user.
**Evidence:** A sign-up request with `{"role": "admin"}` → the user is stored as an admin and passes every admin check.
**Confidence:** High
**Fix:** Copy only `email` and `name` from the parsed body.

### Potential Bugs — Warning

**Location:** `src/api/users.ts:22`
**Issue:** `page` from the query string is compared with `===` against a number.
**Evidence:** `GET /users?page=2` → `page === 2` is false because `page` is the string `"2"`, and the handler returns the first page.
**Confidence:** High
**Fix:** Parse `page` with `Number()` before comparing it.

### Security — Warning

**Location:** `src/api/users.ts:30`
**Issue:** The error response includes the database error message.
**Evidence:** Signing up with an email that already exists → the response shows the table and constraint names.
**Confidence:** High
**Fix:** Return a generic message and log the database error.

### Potential Bugs — Warning

**Location:** `src/api/users.ts:40`
**Issue:** `updatedAt` is taken from the request instead of the server clock.
**Evidence:** A client whose clock is one hour behind → the user looks older than earlier edits, and the sync job skips it.
**Confidence:** High
**Fix:** Set `updatedAt` on the server.

### Potential Bugs — Critical

**Location:** `src/api/users.ts:50`
**Issue:** `deleteUser` deletes the user before it moves the user's orders, outside a transaction.
**Evidence:** The order transfer fails after the delete → the orders keep a `userId` that no longer exists and drop out of every report.
**Confidence:** High
**Fix:** Move the orders and delete the user in one transaction.

### Performance — Suggestion

**Location:** `src/api/orders.ts:8`
**Issue:** The currency formatter is created again for every order of the page.
**Evidence:** A page of 50 orders → 50 formatters are built where one would do; the work is bounded by the page size.
**Confidence:** High
**Fix:** Create the formatter once, outside the loop.

### Potential Bugs — Warning

**Location:** `src/api/orders.ts:12`
**Rule:** `.code-review/rules/validate-request-bodies.md:L7-L8`
**Issue:** The handler reads `req.body.quantity` before the body is parsed.
**Evidence:** A request with `"quantity": "2"` → `quantity + 1` gives `"21"` and the order stores 21 items.
**Confidence:** High
**Fix:** Parse the body with `CreateOrderBody` first, as the rule requires.

### Architecture — Warning

**Location:** `src/api/orders.ts:20`
**Issue:** The handler writes `lastOrderAt` to the `users` table directly instead of calling `UserService.touch`, which also clears the user cache.
**Evidence:** A user places an order → the cached user still shows the old `lastOrderAt` for the 10 minutes of the cache.
**Confidence:** High
**Fix:** Call `UserService.touch(userId)`.

### Performance — Warning

**Location:** `src/api/orders.ts:30`
**Issue:** The items of each order are loaded with one query per order.
**Evidence:** A page of 100 orders → 101 queries per request, growing with the page size and the number of orders.
**Confidence:** High
**Fix:** Load the items of the whole page in one query.

## Needs human verification

### Potential Bugs — Warning

**Location:** `src/api/orders.ts:5`
**Issue:** `currency` falls back to `USD` when the store has none.
**Evidence:** A store without `currency` → its totals show in US dollars; a person must check whether such stores exist in production.
**Confidence:** Medium
**Fix:** Fail when the store has no currency.

## Pre-existing issues (not counted)

- src/api/orders.ts:60 — the export endpoint has no authorization check

## Summary

| Category | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security | 1 | 1 | 0 | |
| Performance | 0 | 1 | 1 | |
| Tests/Coverage | 0 | 0 | 0 | |
| Architecture | 0 | 1 | 0 | |
| Code & File Size | 0 | 0 | 0 | |
| Potential Bugs | 1 | 3 | 0 | |
| Accessibility | 0 | 0 | 0 | ✓ |
| Observability | 0 | 0 | 0 | ✓ |
| API Design | 0 | 0 | 0 | |
| Resilience | 0 | 0 | 0 | ✓ |
| DB Migrations | 0 | 0 | 0 | ✓ |
| Concurrency | 0 | 0 | 0 | ✓ |
| i18n | 0 | 0 | 0 | ✓ |
| Privacy/Compliance | 0 | 0 | 0 | ✓ |
| Architecture Patterns | 0 | 0 | 0 | |
| Stack-Specific | 0 | 0 | 0 | |
| **Total** | **2** | **6** | **1** | |

**Verification:** 10 Critical/Warning candidates checked, 1 refuted.
