**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `getPrice` return dollars for display and add `priceLabel` to format that price for the product page (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `priceLabel` is small and has a single job. It formats with `toFixed(2)`, so the label always shows two decimals.
- The changed tests were updated to match the new return value, and the unknown-SKU error test was kept.
- The new doc comment on `getPrice` states the unit it returns.

## Findings

### Potential Bugs — Critical

**Location:** `src/pricing.ts:10`
**Issue:** `getPrice` now returns dollars (`priceCents / 100`). Its other caller, `checkout` in `src/checkout.ts:9`, still treats the result as cents. That caller was not updated, and the type (`number`) does not catch the change.
**Evidence:** `checkout(gateway, 'tee', 1)` → `getPrice('tee')` returns `20` → `amountCents = 20` → `gateway.charge(20)` charges 20 cents instead of 2000, a 100× undercharge. `checkout(gateway, 'mug', 1)` passes `12.5`, a fractional cent amount, to a gateway whose parameter is `amountCents`. Gateways commonly reject or round that, and I could not see this one. Verification checked every `getPrice` reference in the repository. There are three callers: `checkout.ts:9`, which is broken, `price-label.ts:5`, which is updated, and the tests. No test exercises `checkout`, so nothing fails.
**Confidence:** High
**Fix:** Keep `getPrice` returning cents, and do the dollar conversion only for display. For example, have `priceLabel` compute `(getPrice(sku) / 100).toFixed(2)` and revert the `pricing.ts` and `pricing.test.ts` changes. If the dollar contract is intended, update `checkout` to charge cents (`Math.round(getPrice(sku) * 100) * quantity`) and add a `checkout` test. Prefer the first option, because dollar floats multiplied by `quantity` accumulate rounding errors.

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
**Relevant tests:** changed — `src/pricing.test.ts` covers `getPrice('mug')` (12.5) and the unknown-SKU error. `src/price-label.test.ts` covers `priceLabel('mug')` (`$12.50`). No test covers `checkout`, the caller that breaks. Execution: not run.
**Look first:** `src/pricing.ts` (return unit changed from cents to dollars while `src/checkout.ts:9` still expects cents), `src/price-label.ts` (the only caller adapted to the new unit).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 4 of 4 changed files: `src/price-label.test.ts`, `src/price-label.ts`, `src/pricing.test.ts`, `src/pricing.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
