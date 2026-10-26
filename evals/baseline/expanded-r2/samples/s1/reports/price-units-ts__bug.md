Review in progress: I've read the diff and the files around it. `checkout.ts` calls `getPrice` and passes the result to a payment gateway as cents, so the change to `getPrice` looks like a real problem. I'm writing up the report now.

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `getPrice` return dollars and add `priceLabel` to format that price for display (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `priceLabel` is small, has a doc comment, and has a test that shows the expected output (`$12.50`).
- The `pricing.test.ts` expectation and the `getPrice` doc comment were both updated with the new unit, so the tests and comments match the new code.
- `getPrice` still throws on an unknown sku, and its test still covers that.

## Findings

### Potential Bugs — Warning

**Location:** `src/pricing.ts:9`
**Issue:** `getPrice` changes its return unit from cents to dollars (`product.priceCents / 100`). Its existing caller, `checkout`, still treats the result as cents. The change does not update that caller.
**Evidence:** `checkout(gateway, 'mug', 2)` computes `amountCents = getPrice('mug') * 2`, which is now `12.5 * 2 = 25` where it was `1250 * 2 = 2500`. It then calls `gateway.charge(25)`, whose parameter is `amountCents`. The customer is charged 100 times too little, and any non-integer dollar price would send a fractional cent amount. Verification read `src/checkout.ts`, the only other importer of `getPrice`, and `src/catalog.ts`, where prices are stored as `priceCents`. Nothing in the repository converts the value back, and no test covers `checkout`, so nothing catches the break.
**Confidence:** High
**Fix:** Keep `getPrice` in cents and convert in `priceLabel` (`(getPrice(sku) / 100).toFixed(2)`). Revert the `src/pricing.ts` and `src/pricing.test.ts` changes. If `getPrice` must return dollars, update `checkout` to multiply by 100 and round before charging, and add a `checkout` test that asserts the amount passed to `gateway.charge`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 1       | 0          |     |
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
| **Total**             | **0**    | **1**   | **0**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 4 files; payments.
**Relevant tests:** changed — `src/pricing.test.ts` covers `getPrice('mug')` returning `12.5` and the unknown-sku error. `src/price-label.test.ts` covers `priceLabel('mug')` returning `'$12.50'`. No test covers `checkout`, so none would catch the cents/dollars mismatch. Execution: not run.
**Look first:** `src/pricing.ts` (the return unit of `getPrice` changes while `checkout` still treats it as cents), `src/pricing.test.ts` (its expectation was rewritten to the new unit, hiding the contract change).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 4 of 4 changed files: `src/price-label.test.ts`, `src/price-label.ts`, `src/pricing.test.ts`, `src/pricing.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
