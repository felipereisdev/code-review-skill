**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: switch `formatPrice` to `Intl.NumberFormat` so prices get thousands separators (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The `Intl.NumberFormat` instance is created once at module level, so each call doesn't build a new formatter.
- The change adds a test for the new behavior (`1234.5` → `$1,234.50`) next to the existing one.

## Findings

### Potential Bugs — Warning

**Location:** `src/format.js:3-6` (the removed guard was old lines 4-6)
**Issue:** The change removes the `amount == null` guard that returned `'—'`. `Intl.NumberFormat#format` does not return a dash for missing values: it treats `null` as `0` and `undefined` as `NaN`.
**Evidence:** `src/cart.js:9` calls `formatPrice(item.salePrice)` for every cart item. For an item with no sale price, `salePrice` is `null` or `undefined`. With the new code, `null` gives `"$0.00"` and `undefined` gives `"$NaN"`, so the cart shows a free or garbled sale price. Commit 22bdef7's message says "fix: show a dash for items that are not on sale (#64)", and `git blame` shows it last changed the removed lines. The change undoes that fix, and nothing in the diff replaces the guard. Verification checked the only caller, `src/cart.js:6-10`, and the tests in `test/format.test.js`. Neither stops a missing value from reaching `formatPrice`, and no test covers the dash.
**Confidence:** High
**Fix:** Restore the guard above the `Intl` call: `if (amount == null) { return '—'; }`, then `return usd.format(amount);`.

### Tests/Coverage — Suggestion

**Location:** `test/format.test.js:10-12`
**Issue:** The added test covers only the thousands separator. Nothing tests `formatPrice(null)` or `formatPrice(undefined)`, the dash behavior that #64 added.
**Evidence:** The guard is removed and `node --test` still passes, because no test asserts `'—'` for a missing value. That is how the regression above goes unnoticed.
**Confidence:** High
**Fix:** Add `assert.strictEqual(formatPrice(null), '—')` and the same for `undefined`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 1       | 0          |     |
| Accessibility         |          |         |            | N/A |
| Observability         |          |         |            | N/A |
| API Design            |          |         |            | N/A |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **1**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/format.test.js` adds a check of `formatPrice(1234.5)` → `$1,234.50` and keeps the `4.5` → `$4.50` check; no test covers `null` or `undefined` input. Execution: not run.
**Look first:** `src/format.js` (the removed null guard makes `cart.js` show `$0.00` or `$NaN` for items with no sale price), `test/format.test.js` (no test for the dash).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`, `src/cart.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
