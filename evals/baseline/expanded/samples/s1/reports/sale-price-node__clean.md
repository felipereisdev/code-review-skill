## Intent

**Intent:** inferred: move the "not on sale" dash from `formatPrice` into `cartRows`, and format prices with `Intl.NumberFormat` so thousands get a separator (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

**Scope:** staged (git diff --cached)

## What Was Done Well

- Moving the `null` check to the only call site (`src/cart.js:9`) keeps the dash for `salePrice: null` and `undefined`. `== null` covers both, so the cart output for the catalog items does not change.
- The `Intl.NumberFormat` instance is created once at module load (`src/format.js:3`). It is not rebuilt on every call.
- The change adds a test for the new thousands-separator behavior (`test/format.test.js:11-13`).

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/cart.js:9`
**Issue:** The "dash when not on sale" behavior now lives in `cartRows`, but no test covers it. This is the behavior that commit `22bdef7` ("fix: show a dash for items that are not on sale (#64)") introduced. The only test file is `test/format.test.js`, and it never calls `cartRows`.
**Evidence:** Someone edits the `salePrice == null` condition, for example to `salePrice === null` or `!item.salePrice`. Items with `salePrice: undefined` then print `$NaN`, or items with `0` print `—`. No test fails, because no test runs `cartRows` and the old `formatPrice(null)` test never existed.
**Confidence:** High
**Fix:** Add a `test/cart.test.js` that calls `cartRows` with one item that has a `salePrice` and one with `salePrice: null`. Assert `sale` is `'$3.99'` for the first and `'—'` for the second.

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

**Verification:** 1 Critical/Warning candidates checked, 1 refuted.

The refuted candidate was the `null` guard removed from `formatPrice` (`src/format.js`). It would have made `formatPrice(null)` return `$0.00` and `formatPrice(undefined)` return `$NaN`. Verification found only one caller, `cartRows` in `src/cart.js`. It guards `salePrice` itself and passes `price` unguarded. `src/catalog.js` gives every item a non-null `price`, so no reachable input triggers the new behavior.

**Review effort:** 1/5 — up to 50 changed lines in 3 files; no risk area.
**Relevant tests:** changed — `test/format.test.js` covers `formatPrice(4.5)` and `formatPrice(1234.5)`, but nothing covers `cartRows` or the dash for a null `salePrice`. Execution: not run.
**Look first:** `src/cart.js` (the dash logic moved here and has no test), `src/format.js` (the `null` guard was removed and the output now comes from `Intl.NumberFormat`).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 3 of 3 changed files: `src/cart.js`, `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`, `src/catalog.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
