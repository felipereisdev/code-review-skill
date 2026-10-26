**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: format prices with a thousands separator through `Intl.NumberFormat`, and move the "not on sale" dash from `formatPrice` into `cartRows` (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The dash for an item that is not on sale is still produced for `salePrice`, now at the call site in `src/cart.js:9`. It covers both `null` and `undefined` through `== null`.
- The `Intl.NumberFormat` instance is created once at module load, not on every `formatPrice` call.
- A new test, `test/format.test.js:11-13`, covers the thousands separator that motivates the change.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/cart.js:9`
**Issue:** The new `salePrice == null ? '—' : formatPrice(item.salePrice)` branch has no test. The `formatPrice` null case was not tested before either, and its guard is now gone.
**Evidence:** Someone later changes or removes the guard in `cartRows` → nothing fails, because `test/` holds only `format.test.js` and no test calls `cartRows`. Pencil case, with `salePrice: null`, would then silently show `$0.00` instead of `—`.
**Confidence:** High
**Fix:** Add a `test/cart.test.js` that runs `cartRows` over `src/catalog.js` items, or an inline `{ price: 7.25, salePrice: null }`, and asserts `sale === '—'`.

## Needs human verification

### Potential Bugs — Warning

**Location:** `src/format.js:6`
**Issue:** `formatPrice` no longer handles a missing amount. The change moves the null guard to `cartRows` for `salePrice` only, so `item.price` is now unguarded.
**Evidence:** `cartRows([{ name: 'X', price: null }])` → `formatPrice(null)` returns `$0.00`, because `Intl.NumberFormat#format(null)` formats it as 0, where it used to return `—`. With `price` undefined, the result is `$NaN`. A priceless item would then appear as free or as `$NaN` in the cart. Verification read `src/cart.js` and `src/catalog.js`. `cartRows` is the only caller of `formatPrice` in the repository, and every `price` in `src/catalog.js` is a number. A person must check whether `item.price` can be `null` or `undefined` in the real input of `cartRows`, which the repository does not show. History: git blame at `60dc4c2` shows `22bdef7` last changed the removed guard lines, and its message says "fix: show a dash for items that are not on sale (#64)". The code shows that this fix still holds for `salePrice`.
**Confidence:** Medium
**Fix:** If `price` can be missing, guard it too, for example with a shared helper such as `const orDash = (v) => (v == null ? '—' : formatPrice(v))` used for both fields. Otherwise keep the change as it is.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
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
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 3 files; no risk area.
**Relevant tests:** changed — `test/format.test.js` runs `formatPrice` on 4.5 and 1234.5 (decimals and thousands separator). It leaves out `null` and `undefined` amounts and every `cartRows` branch. Execution: not run.
**Look first:** `src/format.js` (the null guard was removed and the finding under Needs human verification is about it), `src/cart.js` (the guard now covers `salePrice` only, and no test covers it).
**Ready to merge:** With fixes — a person must check 1 finding under Needs human verification before merging.

## Audit

**Files reviewed:** 3 of 3 changed files: `src/cart.js`, `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`, `src/catalog.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
