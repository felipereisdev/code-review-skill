**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship gift orders to the gift recipient's address instead of the buyer's (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and focused. The new `giftRecipientId` branch is a single, readable line.
- The test `ships gifts to the recipient` covers the new happy path with a concrete expected label.
- The existing tests for the unknown-customer and normal-label cases are unchanged and still describe the old behavior.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** `recipient` is looked up with `customers.get(order.giftRecipientId)` and used without a guard. The existing code returns `null` when the buyer is unknown, but the new lookup has no such check.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined`, so `recipient.name` on line 14 throws `TypeError: Cannot read properties of undefined (reading 'name')`. Any order whose gift recipient is not in `customers` crashes label generation. Before this change the same order produced a label. Verification checked the whole repository: `shippingLabel` is called only from `test/labels.test.js`, and no test, guard or type rules the scenario out. The only other recipient ids the tests use are existing customers.
**Confidence:** High
**Fix:** Apply the same guard the function already uses for the buyer, and add a test for it:
```js
  const recipient = order.giftRecipientId ? customers.get(order.giftRecipientId) : customer;
  if (!recipient) {
    return null;
  }
  return [recipient.name, recipient.address.street, recipient.address.city].join('\n');
```
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

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient`, which covers a gift order whose recipient exists; it leaves out a gift recipient that is not in `customers`. Execution: not run.
**Look first:** `src/labels.js` (Critical: unguarded `recipient` throws a `TypeError` for an unknown gift recipient), `test/labels.test.js` (no test for an unknown gift recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/fix.md`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.

## Fix proposal

1. `src/labels.js:13-14` Critical — Potential Bugs: after line 13, add `if (!recipient) { return null; }` so an unknown gift recipient returns `null` instead of throwing.

Fix not applied: no fix was approved before this headless run; no file was changed. The report above is complete.
