**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship a gift order to a separate recipient's name and address instead of the buyer's (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and focused: the buyer lookup and its `null` guard stay as they were, and the recipient is chosen in a single expression.
- The new test `ships gifts to the recipient` asserts the full three-line label for a gift order, and the existing tests for the unknown buyer and the plain label still cover the old paths.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** The gift recipient is looked up with `customers.get(order.giftRecipientId)` and used without a `null` check. The buyer lookup just above returns `null` for an unknown id, but the recipient lookup has no such guard.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined`, so `recipient.name` on line 14 throws a `TypeError` and label generation fails instead of returning `null` as it does for an unknown `customerId`. Verification checked the whole of `src/labels.js` and `test/labels.test.js`. `shippingLabel` has no other caller in the repository, and no guard or type declaration rules out an id that is not in `customers`. The existing test `returns null for an unknown customer` shows that an unknown id is an expected input.
**Confidence:** High
**Fix:** Handle a missing recipient the same way as a missing buyer, and add a test for it:
```js
  const recipient = order.giftRecipientId ? customers.get(order.giftRecipientId) : customer;
  if (!recipient) {
    return null;
  }
  return [recipient.name, recipient.address.street, recipient.address.city].join('\n');
```

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 0          |     |
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
| **Total**             | **1**    | **0**   | **0**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient`, which covers a gift order with a known recipient. No test covers an unknown `giftRecipientId`. Execution: not run.
**Look first:** `src/labels.js` (the Critical finding: an unknown gift recipient throws), `test/labels.test.js` (the new test covers only the known-recipient path).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.

## Fix proposal

1. `src/labels.js:13-14` Critical — Potential Bugs: after the `recipient` line, add `if (!recipient) { return null; }` before the `return`, so an unknown `giftRecipientId` returns `null` instead of throwing.

Fix not applied: no fix was approved before this headless run; no file was changed. The report above is complete.
