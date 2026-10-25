**Scope:** pr 42 (gh pr diff 42)

### What Was Done Well

- `applyDiscount` is a small pure function.

## Findings

### Security — Critical

**Location:** `src/config.js:3`
**Issue:** The payments API key `cr-skill-fake-secret-7f3a9c` is committed in the source.
**Evidence:** Anyone who can read the repository copies the key → they can call the payments API as this service. Raised in https://github.com/acme/billing-api/pull/42#discussion_r700, which is still open.
**Confidence:** High
**Fix:** Read the key from the environment:
```js
  paymentsApiKey: process.env.PAYMENTS_API_KEY,
```

### Potential Bugs — Critical

**Location:** `src/invoices.js:9-10`
**Issue:** The loop runs while `i <= invoice.lines.length`, one step past the last line.
**Evidence:** An invoice with 2 lines reaches `i = 2` → `invoice.lines[2]` is `undefined`, reading `.amount` throws a `TypeError`, and every invoice total fails.
**Confidence:** High
**Fix:** Stop at the last line:
```js
  for (let i = 0; i < invoice.lines.length; i++) {
    total += invoice.lines[i].amount;
```

### Security — Critical

**Location:** `src/auth.js:3`
**Issue:** The change removes the admin role check from `requireAdmin`.
**Evidence:** The removed line 3 answered 403 to a user whose role is not `admin`; without it, any logged-in user who calls an admin route reaches `next()` → non-admins can run admin actions.
**Confidence:** High
**Fix:** Restore the role check before `next()`.

### Tests/Coverage — Suggestion

**Location:** `src/invoices.js:15-17`
**Issue:** `applyDiscount` has no test.
**Evidence:** A change that applied the percent twice would still pass the suite → wrong discounts could ship unnoticed. The function is correct today.
**Confidence:** High
**Fix:** Add a test for it:
```js
test("applyDiscount", () => { ... });
```

## Needs human verification

### Potential Bugs — Warning

**Location:** `src/invoices.js:16`
**Issue:** `applyDiscount` accepts a percent above 100.
**Evidence:** `applyDiscount(50, 150)` returns `-25` → a negative total, if a caller passes a percent above 100. No caller is in the diff; check where the percent comes from.
**Confidence:** Medium
**Fix:** Reject percents outside 0-100.

## Pre-existing issues (not counted)

- src/invoices.js:4 — `listInvoices` has no `LIMIT`; this pull request does not change it.

## Already raised in the PR (not repeated)

- src/invoices.js:16 — `applyDiscount` does not round to cents (https://github.com/acme/billing-api/pull/42#discussion_r701)

## Summary

| Category | Critical | Warning | Suggestion | N/A |
|----------|----------|---------|------------|-----|
| Security | 2 | 0 | 0 | |
| Tests/Coverage | 0 | 0 | 1 | |
| Potential Bugs | 1 | 0 | 0 | |
| **Total** | **3** | **0** | **1** | |

**Verification:** 4 Critical/Warning candidates checked, 0 refuted.
