**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: move the "not on sale" dash from `formatPrice` into `cartRows`, and format prices with `Intl.NumberFormat` so thousands get a separator (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The null check moved to the only call site that can receive a null (`src/cart.js:9`). The `—` for items not on sale still shows up in the cart.
- The `Intl.NumberFormat` instance is built once at module load (`src/format.js:3`) and reused on every call.
- The change adds a test for the new thousands separator (`test/format.test.js:11-13`).

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/cart.js:9`
**Issue:** The `—` for a null `salePrice` now lives in `cartRows`, but no test runs `cartRows` or any null `salePrice`.
**Evidence:** The change removes the `amount == null` branch from `formatPrice`, so `formatPrice(null)` no longer returns `—`. The branch was added by the bug fix in `22bdef7` (#64); its message says "formatPrice(null) threw a TypeError and broke the cart for any item without a sale price". Someone who removes or reverses the guard at `src/cart.js:9` would break the cart again and every test would still pass. `test/format.test.js` only covers `formatPrice(4.5)` and `formatPrice(1234.5)`. No other test file exists.
**Confidence:** High
**Fix:** Add a test for `cartRows` using an item with `salePrice: null` (for example the "Pencil case" item in `src/catalog.js`) that asserts `sale` is `'—'`. Add one for an item with a sale price that asserts `$3.99`.

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
**Relevant tests:** changed — `test/format.test.js` runs `formatPrice` for `4.5` and `1234.5` (two decimals and a thousands separator). No test covers `cartRows`, a null `salePrice`, or `formatPrice` with null, undefined or negative input. Execution: not run.
**Look first:** `src/cart.js` (the null guard now lives here and has no test), `src/format.js` (the removed null guard changes what `formatPrice` returns for non-numbers).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 3 of 3 changed files: `src/cart.js`, `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`, `src/catalog.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
