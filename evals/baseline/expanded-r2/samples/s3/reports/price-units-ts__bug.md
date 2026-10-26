**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: show a dollar-formatted price label (`priceLabel`) by making `getPrice` return dollars instead of cents (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `priceLabel` is small and does one thing. It reuses `getPrice`, so unknown SKUs still throw.
- `getPrice` keeps its test, including the unknown-SKU case, and the new `priceLabel` has a test.

## Findings

### Potential Bugs — Critical

**Location:** `src/pricing.ts:9`
**Also at:** `src/pricing.ts:3`, `src/pricing.test.ts:5-6`
**Issue:** `getPrice` changes its contract from cents to dollars (`product.priceCents / 100`). The name and `number` type stay the same, so `tsc` cannot flag callers that still expect cents. `src/checkout.ts:9` (not in the diff) still treats the value as cents: `const amountCents = getPrice(sku) * quantity;` then `gateway.charge(amountCents)`.
**Evidence:** `checkout(gateway, 'mug', 2)` → `getPrice('mug')` now returns `12.5`, so `amountCents` is `25` instead of `2500`. The gateway receives a charge 100 times too small, and the amount is fractional for odd prices, for example `12.5 * 1`. Customers are undercharged, or the gateway rejects the non-integer amount and checkout fails. Verification checked the only other caller of `getPrice` (`src/checkout.ts`), the types (`number` on both sides), and the tests. No test covers `checkout`, and the updated `pricing.test.ts` asserts the new dollar value, so nothing catches the break.
**Confidence:** High
**Fix:** Keep `getPrice` returning cents, which is the unit `checkout` and the gateway use. Do the conversion where it is displayed: `` return `$${(getPrice(sku) / 100).toFixed(2)}`; `` in `priceLabel`. Restore the cents doc comment and the `1250` assertion in `pricing.test.ts`. Add a `checkout` test that asserts the amount passed to `gateway.charge`.

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

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 4 files; payments.
**Relevant tests:** changed — `src/pricing.test.ts` asserts `getPrice('mug')` is `12.5` and keeps the unknown-SKU rejection test. `src/price-label.test.ts` asserts `priceLabel('mug')` is `$12.50`. Nothing tests `checkout`, which consumes `getPrice`, and there is no test of an unknown SKU through `priceLabel`. Execution: not run.
**Look first:** `src/pricing.ts` (changes the unit `getPrice` returns, which breaks the cents arithmetic in `src/checkout.ts`), `src/pricing.test.ts` (the updated assertion locks in the dollar contract).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 4 of 4 changed files: `src/price-label.test.ts`, `src/price-label.ts`, `src/pricing.test.ts`, `src/pricing.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
