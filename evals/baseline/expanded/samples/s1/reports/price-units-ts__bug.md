## Scope

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: change `getPrice` to return dollars and add a `priceLabel` helper that formats a SKU's price for display (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `src/price-label.ts` is a small function with a doc comment and uses `toFixed(2)` for display.
- Tests cover the new `priceLabel` and the unknown-SKU error path of `getPrice`.
- The old doc comment on `getPrice` was updated with the unit change.

## Findings

### Potential Bugs — Critical

**Location:** `src/pricing.ts:9`
**Issue:** `getPrice` changed from returning cents to returning dollars (`product.priceCents / 100`), but `src/checkout.ts` still treats its result as cents and passes it to the payment gateway. This is a broken contract with an existing caller that the diff does not update.
**Evidence:** `checkout(gateway, 'mug', 1)` → `getPrice('mug')` now returns `12.5` → `amountCents = 12.5 * 1` → `gateway.charge(12.5)`, whose parameter is `amountCents` (`src/checkout.ts:4`). The customer is charged 12.5 cents, or a fractional-cent amount the gateway may reject, instead of 1250 cents. `checkout(gateway, 'tee', 2)` charges 40 instead of 4000. Both callers of `getPrice` were checked: `src/price-label.ts` expects dollars, and `src/checkout.ts:9` expects cents. The call type-checks because both sides are `number`, so `tsc` does not catch it. No test covers `checkout`, and the changed tests only assert the new dollar value.
**Confidence:** High
**Fix:** Keep `getPrice` returning cents, as before. Do the conversion in `priceLabel`, for example `` `$${(getPrice(sku) / 100).toFixed(2)}` ``. Revert the `getPrice` test and doc comment to cents. Add a `checkout` test that asserts the amount passed to `gateway.charge`.

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
**Relevant tests:** changed — `src/price-label.test.ts` covers `priceLabel('mug')` returning `$12.50`. `src/pricing.test.ts` covers `getPrice('mug')` returning `12.5` and the unknown-SKU error. No test runs `checkout`, the caller that breaks. Execution: not run.
**Look first:** `src/pricing.ts` (return unit changed from cents to dollars, which breaks `src/checkout.ts`), `src/pricing.test.ts` (asserts the new dollar contract and no test guards the caller).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 4 of 4 changed files: `src/price-label.test.ts`, `src/price-label.ts`, `src/pricing.test.ts`, `src/pricing.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
