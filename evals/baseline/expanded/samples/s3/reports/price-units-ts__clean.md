**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add `priceLabel(sku)`, which formats a product's unit price as a dollar string, with a test (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `priceLabel` is a small pure function that reuses `getPrice` instead of duplicating catalog lookup. It keeps prices as integer cents until the last step, so `toFixed(2)` never formats a fractional-cent value.
- The JSDoc states the output shape, and the new files follow the style of `src/pricing.ts` and `src/pricing.test.ts`.
- The change adds a test next to the new code, and the test's expected value (`$12.50`) matches the catalog price of `mug` (1250 cents).

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/price-label.test.ts:4-8`
**Issue:** The only test covers `mug`, a price that has a whole-dollar part and two decimal digits. It does not cover a sub-dollar amount, a whole-dollar amount, or an unknown SKU.
**Evidence:** A later change to the formatting, such as swapping `toFixed(2)` for `Math.round` or dropping the `/ 100`, would still pass for most single-input checks. A price like `5` cents (`$0.05`) or `2000` cents (`$20.00`) would catch it. `priceLabel('hat')` throws `unknown sku: hat` through `getPrice`, but no test records that this is the intended behavior for the label.
**Confidence:** High
**Fix:** Add a case for `tee` (`$20.00`), and one for the unknown-SKU error: `expect(() => priceLabel('hat')).toThrow('unknown sku: hat')`.

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
**Relevant tests:** changed — `src/price-label.test.ts` checks that `priceLabel('mug')` returns `$12.50`. It leaves out other products, sub-dollar amounts and the unknown-SKU error. `src/pricing.test.ts` already covers `getPrice` and the unknown-SKU error. Execution: not run.
**Look first:** `src/price-label.ts` (the new formatting function, the only behavior in the change), `src/price-label.test.ts` (single-case test).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/price-label.test.ts`, `src/price-label.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `src/pricing.test.ts`, `src/pricing.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
