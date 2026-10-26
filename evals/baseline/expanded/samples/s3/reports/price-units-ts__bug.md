**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: change `getPrice` to return dollars for display and add `priceLabel` to format that price (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The tests in `src/pricing.test.ts` were updated together with the `getPrice` change. The new `src/price-label.test.ts` checks the exact `"$12.50"` output.
- The JSDoc on `getPrice` was updated to describe the new unit.
- `priceLabel` is a small pure function with a clear contract.

## Findings

### Potential Bugs — Warning

**Location:** `src/pricing.ts:9`
**Issue:** `getPrice` now returns dollars (`product.priceCents / 100`), but `checkout` still treats its result as cents. `src/checkout.ts:9` computes `amountCents = getPrice(sku) * quantity`, and `PaymentGateway.charge` takes `amountCents`. This is a changed return contract that was not applied to this caller. The unchanged `src/checkout.ts` was not updated, and the changed line in `src/pricing.ts` triggers the problem.
**Evidence:** `checkout(gateway, 'mug', 2)` → `getPrice('mug')` returns `12.5` → `gateway.charge(25)`. The customer is charged 25 cents instead of 2500 (a 100× undercharge). With `quantity` 1 the amount is `12.5`, a fractional cent amount. Verification searched the repo for `getPrice` callers. `checkout` is the only caller besides `priceLabel`, and no test covers `checkout`, so nothing fails. `getPrice` is typed `number` before and after, so the type checker cannot flag the unit change.
**Confidence:** High
**Fix:** Keep `getPrice` in cents (revert `pricing.ts` and `pricing.test.ts`). Do the dollar conversion only in `priceLabel`, for example `` `$${(getPrice(sku) / 100).toFixed(2)}` ``. This also keeps money out of floating point on the payment path. Alternatively, add a separate display function and leave `getPrice` unchanged. Add a `checkout` test that asserts the amount passed to `gateway.charge`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 1       | 0          |     |
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
| **Total**             | **0**    | **1**   | **0**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 4 files; payments.
**Relevant tests:** changed — `src/pricing.test.ts` covers `getPrice('mug')` returning `12.5` and the unknown-sku error, and `src/price-label.test.ts` covers `priceLabel('mug')` returning `"$12.50"`. Nothing covers `checkout` (looked in `src/`; there is no `src/checkout.test.ts`), so the changed unit contract with its payment caller is untested. Execution: not run.
**Look first:** `src/pricing.ts` (return unit changed from cents to dollars while `src/checkout.ts` still charges `amountCents`), `src/price-label.ts` (new consumer of the dollar value).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 4 of 4 changed files: `src/price-label.test.ts`, `src/price-label.ts`, `src/pricing.test.ts`, `src/pricing.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
