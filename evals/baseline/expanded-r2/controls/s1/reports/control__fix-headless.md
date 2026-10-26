**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship gift orders to the gift recipient's address instead of the buyer's (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and does one thing: it picks the recipient in one line and leaves the rest of `shippingLabel` as it was.
- Orders without `giftRecipientId` still use the buyer through the ternary's fallback, so the existing `formats the label` test is unaffected.
- The new test, `ships gifts to the recipient`, checks the full three-line label for a gift order.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** `recipient` is looked up with `customers.get(order.giftRecipientId)` and used without a null check. The existing guard at lines 10-12 only covers `customer`, the buyer.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined` → `recipient.name` on line 14 throws `TypeError: Cannot read properties of undefined (reading 'name')` and the label request fails. Verification checked every call site: the only one is the new test, which passes a valid id (`2`). Nothing validates `giftRecipientId`, and the `customers` map is the only lookup. The function already returns `null` for an unknown buyer, so an unknown recipient should take the same path.
**Confidence:** High
**Fix:** In `src/labels.js`, add a guard after line 13, so lines 13-14 become:
```js
  const recipient = order.giftRecipientId ? customers.get(order.giftRecipientId) : customer;
  if (!recipient) {
    return null;
  }
  return [recipient.name, recipient.address.street, recipient.address.city].join('\n');
```

### Tests/Coverage — Suggestion

**Location:** `test/labels.test.js:15-20`
**Issue:** The new test covers only a valid recipient. No test covers a `giftRecipientId` that is not in `customers`, which is the path that crashes in the finding above.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` is never run → the `TypeError` at `src/labels.js:14` would stay undetected, or return after a later change, with no failing test.
**Confidence:** High
**Fix:** Add after line 20 of `test/labels.test.js`:
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

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient`, which runs the new branch for a known recipient. It leaves out an unknown `giftRecipientId`, the case that crashes. Execution: not run.
**Look first:** `src/labels.js` (unguarded `recipient` dereference at line 14), `test/labels.test.js` (no test for an unknown recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.

## Fix proposal

1. `src/labels.js:13-14` Critical — Potential Bugs: keep line 13 and insert `if (!recipient) { return null; }` (as a three-line block) before the `return`, so an unknown `giftRecipientId` returns `null` instead of throwing.

Not proposed: `test/labels.test.js:15-20` — Suggestion, not a Critical or Warning finding; the request, which gave only `--fix`, does not name it.

Fix not applied: no fix was approved before this headless run; no file was changed. The report above is complete.
