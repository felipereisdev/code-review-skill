**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add a `priceLabel` helper that formats a SKU's unit price as dollars for display, by changing `getPrice` to return dollars instead of cents (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `src/price-label.ts` is a small, single-purpose function with a doc comment. It reuses `getPrice`, so the unknown-SKU error path is shared rather than duplicated.
- The tests for `getPrice` were updated alongside the behavior change, and `priceLabel` has its own test.

## Findings

### Potential Bugs — Critical

**Location:** `src/pricing.ts:9`
**Issue:** `getPrice` changed its return unit from cents to dollars (`product.priceCents / 100`), and the doc comment and the `getPrice` test were updated. The other caller of `getPrice`, `src/checkout.ts`, was not updated. It still treats the result as cents (`amountCents = getPrice(sku) * quantity`) and passes it to `gateway.charge(amountCents)`. Both values are `number`, so `tsc` cannot catch the mismatch.
**Evidence:** `checkout(gateway, 'mug', 1)` → `getPrice('mug')` now returns `12.5` → `gateway.charge(12.5)` is called where it used to receive `1250`. The customer is charged 100 times too little, and a fractional cent amount is sent for any price that is not a whole dollar. The wrong amount is recorded at the payment gateway on every checkout. Verification checked every use of `getPrice` in the repository (`src/checkout.ts:9` and `src/price-label.ts:5`). Only `price-label.ts` expects dollars. No test covers `checkout`, so nothing fails.
**Confidence:** High
**Fix:** Keep `getPrice` returning cents and do the division in `priceLabel`, for example `(getPrice(sku) / 100).toFixed(2)`. Revert the `pricing.ts` and `pricing.test.ts` changes. If the dollar contract is wanted, update `checkout.ts` to convert back to integer cents (`Math.round(getPrice(sku) * 100) * quantity`) and add a `checkout` test that asserts the amount passed to `gateway.charge`. Renaming the function (for example `getPriceCents` and `getPriceDollars`) would keep a unit change from being silent.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 0          |     |
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
| **Total**             | **1**    | **0**   | **0**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 4 files; payments.
**Relevant tests:** changed — `src/pricing.test.ts` now asserts `getPrice('mug')` is `12.5`, `src/price-label.test.ts` asserts `priceLabel('mug')` is `$12.50`, and the existing unknown-SKU test is unchanged. No test runs `checkout`, so the changed unit is not covered there. Execution: not run.
**Look first:** `src/pricing.ts` (the unit change breaks the cents caller in `src/checkout.ts`), `src/price-label.ts` (the only consumer that expects dollars).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 4 of 4 changed files: `src/price-label.test.ts`, `src/price-label.ts`, `src/pricing.test.ts`, `src/pricing.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
