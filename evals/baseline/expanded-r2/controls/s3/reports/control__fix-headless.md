**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship a gift order to the gift recipient's name and address instead of the buyer's (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and sits in one place. When `giftRecipientId` is absent, the order falls back to the buyer, so existing orders keep the same label.
- A new test covers the gift path and asserts the full three-line label.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** `customers.get(order.giftRecipientId)` has no guard. The `!customer` check at lines 10-12 covers only the buyer, so a recipient that isn't in the map is dereferenced.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined` → `recipient.name` on line 14 throws a `TypeError` and label generation crashes. Before this change an unknown customer returned `null`. Verification checked the whole repository: `shippingLabel` has no caller, validation or schema that restricts `giftRecipientId`, and no test covers an unknown recipient.
**Confidence:** High
**Fix:** Return `null` when the recipient is not found, as the buyer lookup does. Replace line 13 with:
```js
  const recipient = order.giftRecipientId ? customers.get(order.giftRecipientId) : customer;
  if (!recipient) {
    return null;
  }
```

### Tests/Coverage — Suggestion

**Location:** `test/labels.test.js:15-20`
**Issue:** The new test covers only a recipient that exists. The unknown-recipient case, which is the path that crashes, has no test.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → no test exercises it → the crash above goes unnoticed.
**Confidence:** High
**Fix:** After line 20, add:
```js

test('returns null for an unknown gift recipient', () => {
  assert.strictEqual(shippingLabel({ customerId: 1, giftRecipientId: 99 }), null);
});
```

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
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient`, which covers a gift to an existing recipient. It leaves out an unknown `giftRecipientId`. Execution: not run.
**Look first:** `src/labels.js` (the recipient lookup at line 13 has no guard and throws on an unknown id), `test/labels.test.js` (no test for an unknown recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.

## Fix proposal

1. `src/labels.js:13` Critical — Potential Bugs: replace line 13 with the same line followed by `if (!recipient) { return null; }`, so an unknown gift recipient returns `null` instead of throwing.
2. `test/labels.test.js:15-20` Suggestion — Tests/Coverage: add the test `returns null for an unknown gift recipient` after line 20.

Fix not applied: no fix was approved before this headless run; no file was changed. The report above is complete.
