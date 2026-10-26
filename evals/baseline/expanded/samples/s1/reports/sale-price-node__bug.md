**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: format prices with a shared `Intl.NumberFormat` so thousands get a separator (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- Moving to one module-level `Intl.NumberFormat` instance avoids building a formatter on every call.
- The new test asserts the exact output (`$1,234.50`), so it checks behavior and not implementation.

## Findings

### Potential Bugs — Warning

**Location:** `src/format.js:6` (the change also removes old lines 4-6, the `amount == null` guard)
**Issue:** The change removes the `amount == null` guard that returned `'—'`. `formatPrice(null)` now returns `$0.00` and `formatPrice(undefined)` now returns `$NaN`.
**Evidence:** `cartRows` calls `formatPrice(item.salePrice)` (`src/cart.js:9`), and the catalog marks `salePrice` as `null` for items that are not on sale (`src/catalog.js:3-7`, "Pencil case"). With the change, that item's sale column goes from `—` to `$0.00`, so the cart shows the item as free. Verification checked both callers (`src/cart.js`, `src/catalog.js`) and the test file. Nothing else guards null, and no test covers it. `Intl.NumberFormat.prototype.format` converts `null` to the number 0, per ECMA-402, so it does not throw and does not return the dash. I could not run Node to confirm this, because the call was denied, so it rests on the spec. History: git blame at `16feb34` shows `22bdef7` last changed the removed lines; its message says "fix: show a dash for items that are not on sale (#64)" and that `formatPrice(null)` threw a `TypeError` and broke the cart for any item without a sale price. The removal brings back the not-on-sale display problem in a new form.
**Confidence:** High
**Fix:** Restore the guard before formatting: `if (amount == null) { return '—'; }`, then `return usd.format(amount);`. The caller on `src/cart.js:9` also depends on this.

### Tests/Coverage — Suggestion

**Location:** `test/format.test.js:10-13`
**Issue:** The new test covers only a positive number. No test covers `null` or `undefined`, the input that #64 fixed.
**Evidence:** The test suite stays green while `formatPrice(null)` returns `$0.00` instead of `—`, so this regression is not caught.
**Confidence:** High
**Fix:** Add a test such as `assert.strictEqual(formatPrice(null), '—')`, plus the `undefined` case if that is a supported input.

## Pre-existing issues (not counted)

None.

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

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/format.test.js` adds a test that `formatPrice(1234.5)` returns `$1,234.50`, next to the existing two-decimals test; neither covers `null` or `undefined`. Execution: not run.
**Look first:** `src/format.js` (removed null guard changes `formatPrice(null)` from `—` to `$0.00`), `test/format.test.js` (no null case).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`, `src/cart.js`, `src/catalog.js`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
