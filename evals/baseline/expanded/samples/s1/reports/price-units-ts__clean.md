**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add `priceLabel(sku)`, which formats a SKU's unit price as a dollar string such as "$12.50" for the product page (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `priceLabel` is a small pure function. It reuses `getPrice` from `src/pricing.ts` and keeps the price in integer cents until the final formatting step, so floating-point money arithmetic doesn't creep in.
- The doc comment states what the function returns and gives an example.
- The test follows the style of `src/pricing.test.ts`, and its expected value (`'$12.50'`) matches the catalog's 1250 cents for `mug`.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/price-label.test.ts:4-8`
**Issue:** `priceLabel` has only a happy-path test. The error path is untested.
**Evidence:** `priceLabel('hat')` → `getPrice` throws `unknown sku: hat`, and `priceLabel` lets it propagate. Nothing in `src/price-label.test.ts` pins this, so changing `priceLabel` to catch the error or return a fallback label would break no test. The sibling `src/pricing.test.ts` does test the unknown-SKU case for `getPrice`.
**Confidence:** High
**Fix:** Add a case such as `expect(() => priceLabel('hat')).toThrow('unknown sku: hat')`. If the product page should show a fallback for unknown SKUs instead, add that behaviour and test it.

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
**Relevant tests:** changed — `src/price-label.test.ts` checks that `priceLabel('mug')` returns `$12.50`. It does not cover an unknown SKU, and it does not cover prices that aren't whole dollars. Execution: not run.
**Look first:** `src/price-label.test.ts` (only the happy path is tested), `src/price-label.ts` (the new function, whose error behaviour comes from `getPrice`).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/price-label.test.ts`, `src/price-label.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `src/pricing.test.ts`, `src/pricing.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
