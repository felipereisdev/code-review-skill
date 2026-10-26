**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship gift orders to the gift recipient's name and address instead of the buyer's (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and does one thing.
- A test covers the new gift path (`test/labels.test.js:15-20`), and the existing tests for the unknown buyer and the normal label are kept.
- Orders without `giftRecipientId` still use the buyer through the fallback to `customer`, so the old behavior is kept.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** The gift recipient is looked up with `customers.get(order.giftRecipientId)` and used without a null check. The buyer lookup a few lines above returns `null` for an unknown customer, but the recipient has no such guard.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → the buyer exists, so the early return at line 10 is skipped. `customers.get(99)` returns `undefined`, so `recipient.name` at line 14 throws `TypeError: Cannot read properties of undefined (reading 'name')`. Verification searched the repository: the only callers of `shippingLabel` are the tests, none of which passes an unknown `giftRecipientId`, and no other code validates it. The existing test `returns null for an unknown customer` shows that an unknown customer is expected to give `null`, not an exception.
**Confidence:** High
**Fix:** Return `null` when the recipient is not found, as the buyer lookup does:
```js
const recipient = order.giftRecipientId ? customers.get(order.giftRecipientId) : customer;
if (!recipient) {
  return null;
}
```
Add a test for `shippingLabel({ customerId: 1, giftRecipientId: 99 })` that expects `null`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
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
| **Total**             | **1**    | **0**   | **0**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient`, which covers a valid gift recipient. The tests do not cover an unknown `giftRecipientId`, where the finding above crashes. Execution: not run.
**Look first:** `src/labels.js` (Critical: an unknown gift recipient throws a `TypeError`), `test/labels.test.js` (no test for the unknown-recipient case).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
