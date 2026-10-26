**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: format prices with `Intl.NumberFormat` so thousands get a separator, and move the "—" for a missing sale price from `formatPrice` into `cartRows` (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The existing behavior for `salePrice` is kept: `src/cart.js:9` now owns the "—" for items that are not on sale, so the #64 fix still holds for that field.
- The `Intl.NumberFormat` instance is created once at module level (`src/format.js:3`) and reused, not rebuilt on every call.
- The change adds a test for the new thousands-separator output (`test/format.test.js:11-13`).

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/cart.js:9`
**Issue:** The "—" for a missing sale price moved from `formatPrice` into `cartRows`, and no test covers it. `test/` holds only `format.test.js`, and there is no `cartRows` test. The old null check in `formatPrice` had no test either.
**Evidence:** A later edit to `cartRows` or `formatPrice` drops the null handling → items that are not on sale show `$0.00` or `$NaN`, and no test fails.
**Confidence:** High
**Fix:** Add a `test/cart.test.js` that calls `cartRows` with `salePrice` set to `null` and to `undefined` and asserts `'—'`. Add one case with a real sale price.

## Needs human verification

### Potential Bugs — Warning

**Location:** `src/format.js:5-7`, `src/cart.js:8`
**Issue:** The change removes the `amount == null` guard from `formatPrice`, and `cartRows` re-adds it only for `salePrice`. `price: formatPrice(item.price)` on line 8 is now unguarded.
**Evidence:** An item arrives with `price` set to `null` or `undefined` → before the change the row showed `'—'`. Now `Intl.NumberFormat.format(null)` returns `"$0.00"`, so a missing price looks like a free item, and `format(undefined)` returns `"$NaN"`. Verification checked the only caller of `formatPrice` in the repository (`src/cart.js`) and the test suite. The repository has no schema, type or validation that guarantees `item.price` is a number, so I could not confirm or rule out the scenario. A person must check whether `price` can be missing for any item that reaches `cartRows`. If it can, guard it the way `sale` is guarded. If it cannot, drop this finding.
**Confidence:** Medium
**Fix:** Keep the null guard in `formatPrice` so every caller gets it, or guard `price` in `cartRows` the same way as `sale`. Add a test for `null` and `undefined`.

**History:** `git log -S` from `HEAD` lists `22bdef7`, which changed text matching `if (amount == null)`. `git blame` shows `22bdef7` last changed the removed lines; its message says "fix: show a dash for items that are not on sale (#64)". This is a hypothesis only. The code is what limits the finding to the `price` field: the `salePrice` path is still guarded at `src/cart.js:9`.

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

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 3 files; no risk area.
**Relevant tests:** changed — `test/format.test.js` keeps the `formatPrice(4.5)` case and adds `formatPrice(1234.5)` → `'$1,234.50'`. Neither covers `null` or `undefined` input or `cartRows`, which has no test. Execution: not run.
**Look first:** `src/format.js` (the null guard was removed from `formatPrice`), `src/cart.js` (`price` is unguarded, and the sale-price dash moved here).
**Ready to merge:** With fixes — a person must check 1 finding under Needs human verification before merging.

## Audit

**Files reviewed:** 3 of 3 changed files: `src/cart.js`, `src/format.js`, `test/format.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:**
- Shape of the `items` passed to `cartRows` (whether `price` can be `null` or `undefined`) — context not read, not material: the repository has no caller, schema or type for it; the changed behavior itself was judged from the diff.
