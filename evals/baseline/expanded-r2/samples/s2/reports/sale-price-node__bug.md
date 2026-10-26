**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: format prices with a shared `Intl.NumberFormat` currency formatter so that thousands get a separator (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The `Intl.NumberFormat` instance is built once at module level and reused, not rebuilt on every call.
- A new test covers the thousands separator (`1234.5` → `$1,234.50`).

## Findings

### Potential Bugs — Warning

**Location:** `src/format.js:6` (the removed old-side guard at `src/format.js:4-6` causes it)
**Issue:** The change removes the `amount == null` guard that returned `'—'`. `usd.format(amount)` now converts `null` to `0`, so a missing price renders as `$0.00` instead of a dash.
**Evidence:** `cartRows` in `src/cart.js:9` calls `formatPrice(item.salePrice)`, and `src/catalog.js:6` has the item `Pencil case` with `salePrice: null`. → The cart row for that item now shows `sale: '$0.00'` instead of `'—'`, which reads as a free item. This undoes the fix from #64 ("show a dash for items that are not on sale"). An `undefined` price would render as `$NaN`. Verification checked both callers (`cartRows`, `catalog.items`) and the tests. Nothing guards `null` before `formatPrice`, and no test covers it. History: git blame at `69facc7` shows `22bdef7` last changed these lines; its message says "fix: show a dash for items that are not on sale (#64)".
**Confidence:** High
**Fix:** Keep the guard: `if (amount == null) return '—';` before `return usd.format(amount);`.

### Tests/Coverage — Suggestion

**Location:** `test/format.test.js:11-13`
**Issue:** No test covers `formatPrice(null)`, the not-on-sale case. The new test only covers a thousands value, so the removed guard went unnoticed.
**Evidence:** `formatPrice(null)` now returns `$0.00` → every test in `test/format.test.js` still passes, so the regression is not caught.
**Confidence:** High
**Fix:** Add `assert.strictEqual(formatPrice(null), '—')`, and a case for `undefined` if that is a supported input.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
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
| **Total**             | **0**    | **1**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — the new test covers `formatPrice(1234.5)`, and the existing test covers `formatPrice(4.5)`. Nothing covers `null` or `undefined`. Execution: not run.
**Look first:** `src/format.js` (the removed null guard turns missing sale prices into `$0.00`), `test/format.test.js` (no test for the not-on-sale case).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`, `src/cart.js`, `src/catalog.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
