**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: format prices with `Intl.NumberFormat` so thousands get a separator (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- Replacing the hand-built `$${amount.toFixed(2)}` string with one shared `Intl.NumberFormat` instance, created once at module level, is a clean change. It handles grouping and rounding correctly and avoids a new formatter on every call.
- The change comes with a test (`1234.5` → `$1,234.50`) for the new thousands-separator behavior.

## Findings

### Potential Bugs — Warning

**Location:** `src/format.js:3-6`
**Issue:** The change removes the `amount == null` guard that returned `'—'`. `usd.format(null)` now returns `"$0.00"`, and `usd.format(undefined)` returns `"$NaN"`.
**Evidence:** `cartRows` (`src/cart.js:9`) calls `formatPrice(item.salePrice)`, and `src/catalog.js:3-7` sets `salePrice: null` for items that are not on sale, such as "Pencil case". For that item the cart now shows a sale price of `$0.00` instead of `—`, which suggests the item is free. An item with no `salePrice` property at all would show `$NaN`. Verification read both callers and found no other null handling before `formatPrice`; `Intl.NumberFormat.prototype.format` converts `null` to `0` instead of throwing. History: git blame at `e00453b` shows `22bdef7` last changed the removed lines. Its message says "fix: show a dash for items that are not on sale (#64)". The code read above shows the same scenario that fix addressed, in a different form.
**Confidence:** High
**Fix:** Restore the guard in `formatPrice` and keep the new formatter: `if (amount == null) { return '—'; }` before `return usd.format(amount);`.

### Tests/Coverage — Suggestion

**Location:** `test/format.test.js:11-13`
**Issue:** The test file covers only `4.5` and `1234.5`. It has no case for `null` or `undefined`, the input that #64 handled and that this change breaks.
**Evidence:** `formatPrice(null)` now returns `"$0.00"` and no test fails, so the regression in the finding above passes the suite unnoticed.
**Confidence:** High
**Fix:** Add `assert.strictEqual(formatPrice(null), '—')` and an `undefined` case.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
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
| **Total**             | **0**    | **1**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/format.test.js` runs `formatPrice` with `4.5` and, new in this change, `1234.5`. It leaves out `null`, `undefined`, zero and negative amounts. Execution: not run.
**Look first:** `src/format.js` (the removed null guard makes the cart show `$0.00` for items not on sale), `test/format.test.js` (no null or undefined case).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`, `src/cart.js`, `src/catalog.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
