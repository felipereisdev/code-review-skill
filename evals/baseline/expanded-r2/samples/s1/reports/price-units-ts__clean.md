**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add a `priceLabel(sku)` helper that formats a product's unit price, stored in cents, as a dollar string for the product page, with a unit test (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `priceLabel` is a small pure function with one job. It reuses `getPrice` instead of duplicating the catalog lookup (`src/price-label.ts:1-6`).
- Prices stay in integer cents until the last step, so `/ 100` followed by `toFixed(2)` cannot produce a rounding error. `1250` gives `"$12.50"`.
- The doc comment gives an example of the output. The test sits next to the code and follows the style of `src/pricing.test.ts`.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/price-label.test.ts:5-7`
**Issue:** The only test covers the happy path (`'mug'` gives `'$12.50'`). It does not cover an unknown sku, and it does not cover a price that is not a whole dollar amount or that is below one dollar.
**Evidence:** `priceLabel('hat')` calls `getPrice('hat')`, which throws `unknown sku: hat` (`src/pricing.ts:6-8`). The helper has no test that pins this error behavior. A later change that swallows the error, or that returns `"$NaN"`, would pass this suite.
**Confidence:** High
**Fix:** Add a case such as `expect(() => priceLabel('hat')).toThrow('unknown sku: hat')`. Optionally add one for a price below one dollar, so that padding such as `"$0.05"` is asserted.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         | 0        | 0       | 0          | N/A |
| Observability         | 0        | 0       | 0          | N/A |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `src/price-label.test.ts` checks that `priceLabel('mug')` returns `'$12.50'`; it leaves out the unknown-sku error and prices that are not whole dollars. Execution: not run.
**Look first:** `src/price-label.ts` (the only new behavior: cents-to-dollar formatting, with unknown-sku errors passing through from `getPrice`), `src/price-label.test.ts` (happy path only).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/price-label.test.ts`, `src/price-label.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `src/pricing.test.ts`, `src/pricing.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
