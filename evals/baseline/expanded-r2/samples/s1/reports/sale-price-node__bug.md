**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: format prices with `Intl.NumberFormat` so thousands get a separator (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change replaces manual `$${amount.toFixed(2)}` formatting with one module-level `Intl.NumberFormat` instance. It is created once and reused, and it handles grouping separators.
- `test/format.test.js` adds a test for the new thousands-separator behavior (`1234.5` → `$1,234.50`).

## Findings

### Potential Bugs — Warning

**Location:** `src/format.js:3-6`
**Issue:** The change removes the `amount == null` guard that returned `'—'`. `usd.format(null)` now returns `"$0.00"`, and `usd.format(undefined)` returns `"$NaN"`.
**Evidence:** A cart contains an item that is not on sale, such as `Pencil case` in `src/catalog.js:6` with `salePrice: null`. `cartRows` calls `formatPrice(item.salePrice)` (`src/cart.js:9`) → `ToNumeric(null)` is `0`, so the sale column shows `$0.00` instead of `—`. The item appears to be free. An item with no `salePrice` property shows `$NaN`. This brings back the bug that commit #64 fixed. Verification read both callers (`src/cart.js` and `src/catalog.js`), and neither guards against `null`. The only existing test uses `4.5`. History: git blame at `b78849b` shows `22bdef7` last changed the removed lines; its message says "fix: show a dash for items that are not on sale (#64)".
**Confidence:** High
**Fix:** Keep the guard: `if (amount == null) return '—'; return usd.format(amount);`.

### Tests/Coverage — Suggestion

**Location:** `test/format.test.js:11-13`
**Issue:** The new test covers only the separator. No test covers `formatPrice(null)` returning `'—'`, the behavior the removed guard provided, so the regression above passes the suite.
**Evidence:** The suite has only `formatPrice(4.5)` and `formatPrice(1234.5)`. Deleting the `null` guard, as this change does, breaks nothing in the suite, so nothing flags the regression.
**Confidence:** High
**Fix:** Add `assert.strictEqual(formatPrice(null), '—')`, and one for `undefined` if that case should also show a dash.

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
| i18n                  | 0        | 0       | 0          |     |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **1**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/format.test.js` runs `formatPrice` with `4.5` and with `1234.5` (separator); it leaves out `null`, `undefined` and the cart rows. Execution: not run.
**Look first:** `src/format.js` (removed `null` guard turns "not on sale" into `$0.00`), `test/format.test.js` (no test for the `null` case).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/format.js`, `test/format.test.js`.
**Read for context:** `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`, `src/cart.js`, `src/catalog.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, i18n, Stack-Specific.
**Not verified:**
- `package.json` (the `test` script, `node --test`) was read through the permission-denied multi-file read only in part; it was not otherwise needed — not material: no changed behavior depends on it.
