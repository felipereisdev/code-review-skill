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

### Potential Bugs — Critical

**Location:** `src/api/users.ts:50`
**Issue:** `deleteUser` deletes the user before it moves the user's orders, outside a transaction.
**Evidence:** The order transfer fails after the delete → the orders keep a `userId` that no longer exists and drop out of every report.
**Confidence:** High
**Fix:** Move the orders and delete the user in one transaction.

### Potential Bugs — Warning

**Location:** `src/api/orders.ts:12`
**Rule:** `.code-review/rules/validate-request-bodies.md:L7-L8`
**Issue:** The handler reads `req.body.quantity` before the body is parsed.
**Evidence:** A request with `"quantity": "2"` → `quantity + 1` gives `"21"` and the order stores 21 items.
**Confidence:** High
**Fix:** Parse the body with `CreateOrderBody` first, as the rule requires.

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
| Security | 1 | 0 | 0 | off |
| Performance | 0 | 0 | 0 | |
| Tests/Coverage | 0 | 0 | 0 | |
| Architecture | 0 | 0 | 0 | off |
| Code & File Size | 0 | 0 | 0 | |
| Potential Bugs | 1 | 1 | 0 | |
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
| **Total** | **2** | **1** | **0** | |

**Verification:** 10 Critical/Warning candidates checked, 1 refuted.

**Omitted by configuration:** min_severity Warning: 1 omitted; disabled categories Security, Architecture: 2 omitted; max_findings_per_file 2: 3 omitted.
