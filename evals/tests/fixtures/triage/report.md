**Scope:** staged (git diff --cached)

### What Was Done Well

- The new handler validates its input with the route schema.

## Findings

### Security — Critical

**Location:** `src/orders.js:12`
**Issue:** The order query concatenates `req.query.status` into SQL.
**Evidence:** `GET /orders?status=' OR '1'='1` → the query returns the orders of every customer.
**Confidence:** High
**Fix:** Pass the status as a bound parameter.

### Potential Bugs — Warning

**Location:** `src/orders.js:20-22`
**Issue:** The total skips the last order line.
**Evidence:** An order with 3 lines sums lines 0 and 1 → the total is too low.
**Confidence:** High
**Fix:** Loop while `i < lines.length`.

## Needs human verification

### Performance — Warning

**Location:** `src/orders.js:30`
**Issue:** The report loads every order into memory.
**Evidence:** A shop with millions of orders → the request runs out of memory, if no caller limits the date range. Check the callers.
**Confidence:** Medium
**Fix:** Paginate the query.

## Summary

| Category | Critical | Warning | Suggestion | N/A |
|----------|----------|---------|------------|-----|
| Security | 1 | 0 | 0 | |
| Performance | 0 | 0 | 0 | |
| Tests/Coverage | 0 | 0 | 0 | |
| Architecture | 0 | 0 | 0 | |
| Code & File Size | 0 | 0 | 0 | |
| Potential Bugs | 0 | 1 | 0 | |
| **Total** | **1** | **1** | **0** | |

**Verification:** 3 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 3/5 — 120 changed lines in 2 files; payments.
**Relevant tests:** missing — `tests/orders.test.js` is the only test of `src/orders.js`, and it runs neither `listOrders` nor `orderTotal`. Execution: not run.
**Look first:** `src/orders.js` (the SQL injection in the order query, Critical).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/orders.js`, `src/routes.js`.
**Read for context:** 2 files: `package.json`, `tests/orders.test.js`.
**Checked with no findings:** Architecture, Code & File Size.
**Not verified:**
- `pg` query options in `src/orders.js` — API not validated, not material: no documentation tool was available; no changed behavior depends on these options.
