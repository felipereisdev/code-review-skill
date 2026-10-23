## Code Review: staged changes (`src/labels.js`, `test/labels.test.js`)

**Stack detected:** plain Node.js (CommonJS, built-in `node --test`), no framework, no architecture pattern. I didn't load any stack or pattern files, because the generic rules were enough. I didn't run the tests.

### What was done well
- The change is small and focused. The original customer guard stays, and the new `recipient` is guarded the same way.
- Both new paths have tests: a successful gift shipment and an unknown gift recipient. The existing tests still cover the non-gift path.
- The test names say what they check.

### Potential Bugs — Suggestion

**File:** `src/labels.js:13`
**Issue:** `order.giftRecipientId ? ... : customer` uses a truthiness check. A recipient ID of `0` or `''` silently falls back to shipping to the buyer instead of failing. The current IDs start at 1, so this is latent. Still, a gift sent to the wrong address is a costly mistake.
**Fix:** Test explicitly, e.g. `order.giftRecipientId != null`. Alternatively, use `Object.hasOwn(order, 'giftRecipientId')` if "present but invalid" should be an error.

### Potential Bugs — Suggestion

**File:** `src/labels.js:14-16`
**Issue:** An unknown gift recipient returns `null`, the same value as an unknown buyer. Callers can't tell why no label was produced, and a bad gift order may fail without anyone noticing.
**Fix:** If callers need to react differently, throw or return a distinct error for a missing recipient. If `null` is the intended contract, document it.

### Tests/Coverage — Suggestion

**File:** `test/labels.test.js:15-24`
**Issue:** The new tests don't cover these cases:
- a gift recipient with no `address`
- a falsy but present `giftRecipientId` such as `0`
- a gift where the buyer is also the recipient
- a gift order whose buyer (`customerId`) is unknown

The last case is covered only by the existing unknown-customer test, which has no gift ID.
**Fix:** Add a test for the `giftRecipientId: 0` behavior once you decide what it should do. Add one for the unknown buyer with a valid gift recipient.

### Privacy/Compliance — Suggestion

**File:** `src/labels.js:13`
**Issue:** The label now exposes another customer's name and address. That is correct for shipping. The `giftRecipientId` should still be validated upstream, so a user can't enter an arbitrary customer ID and look up other customers' addresses through the label output.
**Fix:** Confirm that the order-creation layer checks the user is allowed to reference that recipient. This is outside this diff.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 2          |     |
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
| **Total**             | **0**    | **0**   | **4**      |     |

There are no blocking issues. The change is safe to merge, and the suggestions are optional hardening.
