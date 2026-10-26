**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship an order that has a gift recipient to the recipient's name and address instead of the buyer's (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and local. The existing `null` guard for an unknown buyer is kept, and orders without `giftRecipientId` still use the buyer's address.
- The diff adds a test for the new gift path, and it checks the whole three-line label.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** `recipient` comes from `customers.get(order.giftRecipientId)` and is dereferenced without a check. The old code returned `null` for an unknown customer. The new gift path has no equivalent guard.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined`, so `recipient.name` throws `TypeError: Cannot read properties of undefined (reading 'name')` and label generation crashes. Verification checked `customers` (a `Map` holding only ids 1 and 2), the only caller (the test file, which has no unknown-recipient case) and the code before line 13. Nothing validates `giftRecipientId` before it reaches the lookup, and the repository has no types or schema that rule the input out.
**Confidence:** High
**Fix:** Handle an unknown recipient the way an unknown customer is handled, by inserting after line 13:
```js
  if (!recipient) {
    return null;
  }
```

### Tests/Coverage — Suggestion

**Location:** `test/labels.test.js:15-20`
**Issue:** The new test covers only a valid gift recipient. The failure path is untested: a `giftRecipientId` that is not in `customers`.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → no test runs it, so the crash above would not be caught by the suite.
**Confidence:** High
**Fix:** Add a test such as `assert.strictEqual(shippingLabel({ customerId: 1, giftRecipientId: 99 }), null);` once the guard exists.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 0          |     |
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
| **Total**             | **1**   | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/labels.test.js` runs `shippingLabel` for an unknown customer, a plain label and the new gift-recipient label. It leaves out an unknown `giftRecipientId`. Execution: not run.
**Look first:** `src/labels.js` (unguarded `recipient` dereference at lines 13-14), `test/labels.test.js` (no test for an unknown gift recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.

## Fix proposal

1. `src/labels.js:13-14` Critical — Potential Bugs: insert after line 13 a guard `if (!recipient) { return null; }` so an unknown `giftRecipientId` returns `null` instead of throwing.

Not proposed: `test/labels.test.js:15-20` — Suggestion, not a Critical or Warning finding, and its Fix is an addition rather than an edit of the reported lines.

Fix not applied: no fix was approved before this headless run; no file was changed. The report above is complete.
