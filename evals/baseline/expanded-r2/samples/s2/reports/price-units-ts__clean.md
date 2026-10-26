**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add `priceLabel(sku)`, which formats a product's unit price as a dollar string for the product page, with a unit test (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `src/price-label.ts` is small and reuses `getPrice` for the price lookup. It adds no second copy of the catalog or the unknown-SKU handling.
- It converts from cents with `toFixed(2)`, which keeps the two-decimal format (`12.5` becomes `"$12.50"`). The TSDoc comment states the output format.
- `src/price-label.test.ts` follows the existing `pricing.test.ts` conventions (vitest, `describe`/`it`). The expected `'$12.50'` matches the catalog's `mug` price of 1250 cents.

## Findings

**Code review passed — no issues found.**

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
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
| **Total**             | **0**    | **0**   | **0**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `src/price-label.test.ts` checks that `priceLabel('mug')` returns `'$12.50'`. It does not cover an unknown SKU or amounts that are not a whole dollar. The `getPrice` unknown-SKU error is covered by `src/pricing.test.ts`. Execution: not run.
**Look first:** `src/price-label.ts` (the only logic added: cents-to-dollars formatting), `src/price-label.test.ts` (single happy-path case).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/price-label.test.ts`, `src/price-label.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/typescript.md`, `src/catalog.ts`, `src/checkout.ts`, `src/pricing.test.ts`, `src/pricing.ts`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
