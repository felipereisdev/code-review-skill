**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: format prices with `Intl.NumberFormat` (USD, thousands separators), and move the "—" for items not on sale from `formatPrice` into `cartRows` (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `src/cart.js:9` keeps the "—" for items that are not on sale. That behavior came from #64, and `src/catalog.js` has an item with `salePrice: null`.
- The `Intl.NumberFormat` instance is built once at module level (`src/format.js:3`) and reused, not rebuilt on every call.
- The new test (`test/format.test.js:11-13`) checks the new thousands-separator behavior.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/cart.js:9`
**Issue:** The change moves the "—" for items not on sale out of `formatPrice` and into `cartRows`, but no test runs `cartRows` or the null-sale-price case.
**Evidence:** A later edit changes the ternary to `formatPrice(item.salePrice)`, so `cartRows` gets `{ salePrice: null }` → it renders `$0.00` instead of `—`, and no test fails. `test/format.test.js` only calls `formatPrice` with numbers, and there is no `cartRows` test.
**Confidence:** High
**Fix:** Add a test that passes `cartRows` an item with `salePrice: null` and expects `sale` to be `'—'`, and one with a numeric `salePrice`.

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
| API Design            |          |         |            | N/A |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 1 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 3 files; no risk area.
**Relevant tests:** changed — `test/format.test.js` adds a `formatPrice(1234.5)` → `'$1,234.50'` case, and the existing `formatPrice(4.5)` case still covers two decimals. Neither covers `cartRows` or null amounts. Execution: not run.
**Look first:** `src/cart.js` (the null-sale-price handling moved here with no test), `src/format.js` (the null guard was removed from `formatPrice`).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 3 of 3 changed files: `src/cart.js`, `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`, `src/catalog.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
