**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add `priceLabel(sku)`, which formats a SKU's unit price as a dollar string for the product page (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `priceLabel` reuses `getPrice` from `src/pricing.ts` and does not copy the catalog lookup.
- The cents-to-dollars conversion is correct: `1250 / 100` gives `12.5`, and `.toFixed(2)` gives `"12.50"`. That matches the new test's expected `$12.50` and the `mug` entry in `src/catalog.ts` (`priceCents: 1250`).
- The new test file sits next to the module and follows the style of `src/pricing.test.ts`. The doc comment says what the function returns.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/price-label.test.ts:4-7`
**Issue:** The only test covers one known SKU. `priceLabel` has no test for an unknown SKU, and none for a price that is not a whole number of dollars. `src/pricing.test.ts` already tests the unknown-SKU case for `getPrice`.
**Evidence:** `priceLabel('hat')` calls `getPrice('hat')`, which throws `unknown sku: hat` (`src/pricing.ts:6-8`). The new test never calls it, so a later change that swallows the error or returns a placeholder label would pass the suite.
**Confidence:** High
**Fix:** Add a case such as `expect(() => priceLabel('hat')).toThrow('unknown sku: hat')`. Optionally add a second SKU whose price is not a round number of dollars.

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

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `src/price-label.test.ts` checks that `priceLabel('mug')` returns `$12.50`. It does not cover an unknown SKU or a non-round price. Execution: not run.
**Look first:** `src/price-label.test.ts` (only the happy path is tested), `src/price-label.ts` (the new formatter).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/price-label.test.ts`, `src/price-label.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `src/pricing.test.ts`, `src/pricing.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
