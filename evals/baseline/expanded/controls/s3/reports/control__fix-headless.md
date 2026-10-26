**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: print a gift order's shipping label with the gift recipient's name and address instead of the buyer's (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change keeps the old behavior when `giftRecipientId` is absent, because `recipient` falls back to `customer`.
- The change adds a test for the new gift path. The expected label text comes from the fixture data for customer 2.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** `recipient` is looked up with `customers.get(order.giftRecipientId)` and then dereferenced with no guard. The `if (!customer)` check above covers only the buyer, not the recipient.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined` → `recipient.name` throws a `TypeError` and the label cannot be produced. Verification searched the repository: the only callers are the tests, and none validates `giftRecipientId`. `customers` is a `Map`, so `get` returns `undefined` for a missing key. Before this change, an unknown customer returned `null`, so the unknown-id case did not throw.
**Confidence:** High
**Fix:** Handle a missing recipient the way the function handles a missing customer. Replace lines 13-14 with:
```js
  const recipient = order.giftRecipientId ? customers.get(order.giftRecipientId) : customer;
  if (!recipient) {
    return null;
  }
  return [recipient.name, recipient.address.street, recipient.address.city].join('\n');
```

### Tests/Coverage — Suggestion

**Location:** `test/labels.test.js:15-20`
**Issue:** The new test covers only a valid `giftRecipientId`. The case of a gift recipient that does not exist is not covered.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` is not tested → the `TypeError` in `src/labels.js:14` goes unnoticed by the suite.
**Confidence:** High
**Fix:** Add this test after line 20:
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
**Relevant tests:** changed — `test/labels.test.js` adds 'ships gifts to the recipient', which covers a valid gift recipient. The existing tests cover an unknown buyer and a plain label. No test covers an unknown gift recipient. Execution: not run.
**Look first:** `src/labels.js` (unguarded `recipient` dereference, Critical), `test/labels.test.js` (no test for an unknown gift recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.

## Fix proposal

1. `src/labels.js:13-14` Critical — Potential Bugs: replace the two lines with the same `recipient` assignment, then `if (!recipient) { return null; }`, then the same `return` line, so an unknown `giftRecipientId` returns `null` instead of throwing.

Not proposed: `test/labels.test.js:15-20` — Suggestion, not proposed: only the Critical finding was listed as a fix.

Fix not applied: no fix was approved before this headless run; no file was changed. The report above is complete.
