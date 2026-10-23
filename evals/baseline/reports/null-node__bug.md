# Code Review — Staged changes (`git diff --cached`)

**Stack detected:** plain Node.js (CommonJS, `node:test`). I applied `stacks/node.md`. No TypeScript, framework, or architecture-pattern files apply.

## What Was Done Well
- The change is small and focused, and it keeps the existing "unknown customer returns null" guard.
- A test covers the new gift-recipient happy path. It asserts the full label string, so it checks behavior and not implementation.

## Findings

### Potential Bugs — Critical

**File:** `src/labels.js:13-14`
**Issue:** `customers.get(order.giftRecipientId)` can return `undefined`. This happens when the ID is not in the map, for example a deleted or mistyped recipient. The next line then dereferences `recipient.name` and throws a `TypeError`. The function already returns `null` for an unknown `customerId`, so an unknown recipient should be handled the same way. The two cases currently behave differently: one returns `null` and the other crashes.
**Fix:** Guard the recipient and keep the existing contract:
```js
const recipient = order.giftRecipientId ? customers.get(order.giftRecipientId) : customer;
if (!recipient) {
  return null;
}
```
Alternatively, fail explicitly with a meaningful error. Either way, don't let a raw `TypeError` escape.

### Potential Bugs — Suggestion

**File:** `src/labels.js:13`
**Issue:** The truthiness check `order.giftRecipientId ?` treats `0` and `''` as "no gift recipient". That is fine for the current IDs, which start at 1. But if an ID of `0` ever becomes valid, the order would silently ship to the buyer.
**Fix:** Use `order.giftRecipientId != null` (or `!== undefined`) to state the intent explicitly.

### Tests/Coverage — Warning

**File:** `test/labels.test.js:14-19`
**Issue:** Only the happy path is covered. There is no test for an unknown `giftRecipientId`, which is the crash above. There is also no test that the buyer's own address is not used when a recipient is set. The existing `customerId: 1` case already covers the no-recipient path.
**Fix:** Add a test such as `shippingLabel({ customerId: 1, giftRecipientId: 99 })`. It should assert `null` (or the chosen error) and act as a regression test for the fix above.

### Privacy/Compliance — Suggestion

**File:** `src/labels.js:13-14`
**Issue:** The order now ships to a different person's address than the buyer's, and the code does not check that the buyer may use that recipient's stored address. Any `giftRecipientId` in an order resolves to another customer's address. If the ID comes from user input, a caller can read other customers' name and address through the label (an IDOR-style exposure).
**Fix:** Confirm where `giftRecipientId` comes from. If it is user-supplied, check that the buyer is allowed to ship to that recipient, for example through an accepted-recipient relationship. Alternatively, store the recipient's address on the order itself.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 1       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 1          |     |
| Accessibility         | 0        | 0       | 0          | N/A |
| Observability         | 0        | 0       | 0          |     |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 1          |     |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **1**   | **2**      |     |

**Verdict:** Do not merge until the unknown-recipient crash is fixed and a test covers it.
