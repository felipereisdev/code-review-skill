**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: format prices through a shared `Intl.NumberFormat` USD formatter (thousands separators), and move the "not on sale" dash from `formatPrice` into `cartRows` (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The dash for items that are not on sale is kept. The null check moved to the one place that knows `salePrice` can be absent, `cartRows`, and `src/catalog.js:3` documents that contract.
- The `Intl.NumberFormat` instance is created once at module load and reused, not rebuilt on every call.
- A test covers the new thousands-separator behavior (`test/format.test.js:11-13`).

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/cart.js:9`
**Issue:** The "dash when not on sale" behavior now lives in `cartRows`. No test covers `cartRows`, and the old null handling in `formatPrice` had no test either.
**Evidence:** A later edit to the `item.salePrice == null ? '—' : ...` branch, such as a refactor that goes back to calling `formatPrice(item.salePrice)` directly, would make "Pencil case" render `$0.00` as its sale price. `test/format.test.js` is the only test file and imports only `formatPrice`, so nothing would fail.
**Confidence:** High
**Fix:** Add a `test/cart.test.js` that runs `cartRows` over `items` from `src/catalog.js` and asserts that `sale` is `'—'` for the item with `salePrice: null`.

## Needs human verification

### Potential Bugs — Warning

**Location:** `src/format.js:5-7`
**Issue:** `formatPrice` no longer returns `'—'` for a missing amount. The exported function now delegates to `Intl.NumberFormat`, which coerces `null` to 0 and `undefined` to `NaN`.
**Evidence:** Trigger: any caller passes `null` or `undefined` to `formatPrice`. Before, it returned `'—'`. Now `formatPrice(null)` returns `'$0.00'` and `formatPrice(undefined)` returns `'$NaN'`, a wrong price shown with no error. In this repository, `src/cart.js` is the only caller. It guards `salePrice` and passes `price`, which `src/catalog.js` always sets, so the scenario does not occur in the code I read. Verification checked every file under `src` and `test`. A person must check whether other code that imports `formatPrice`, outside this repository, relies on the old null handling.
**Confidence:** Medium
**Fix:** Keep the null guard in `formatPrice` (`if (amount == null) return '—';`), or document that callers must filter missing amounts and keep the guard in `cartRows` for `price` too.

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

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 3 files; no risk area.
**Relevant tests:** changed — `test/format.test.js` adds a case for `formatPrice(1234.5)` → `'$1,234.50'` and keeps the `4.5` → `'$4.50'` case. Nothing covers `cartRows`, the dash for `salePrice: null`, or `formatPrice` with a missing amount. Execution: not run.
**Look first:** `src/format.js` (null guard removed from an exported function), `src/cart.js` (the dash logic moved here, untested).
**Ready to merge:** With fixes — a person must check 1 finding under Needs human verification before merging.

## Audit

**Files reviewed:** 3 of 3 changed files: `src/cart.js`, `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`, `src/catalog.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:**
- callers of `formatPrice` outside this repository — context not read, not material: this repository has no other caller, and the changed behavior could be judged without them.
