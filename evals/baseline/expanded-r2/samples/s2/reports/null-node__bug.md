**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship an order to a gift recipient's address when `giftRecipientId` is set, and to the customer's own address otherwise (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The existing `if (!customer) return null` guard is kept, so orders without a gift recipient behave as before.
- The change is small and focused, and it ships with a test for the new gift path. The gift test matches the style of the neighboring tests.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** The gift recipient is looked up with `customers.get(order.giftRecipientId)` and used with no existence check. The customer lookup a few lines above is guarded and returns `null`, but this lookup is not.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined` → `recipient.name` on line 14 throws a `TypeError` and label generation fails. Verification checked the whole repository: `shippingLabel` has no caller other than the tests. No upstream validation, type declaration or test covers an unknown `giftRecipientId`. The only gift test uses the existing id 2.
**Confidence:** High
**Fix:** Handle a missing recipient explicitly, in line with the existing null contract, for example: `if (!recipient) { return null; }` before building the label. If a dangling recipient should be reported as an error instead, throw one with a clear message.

### Tests/Coverage — Suggestion

**Location:** `test/labels.test.js:15-20`
**Issue:** The new test covers only a valid gift recipient. The unknown-recipient case has no test, and that is the case that crashes. The test for an unknown customer is not mirrored for an unknown recipient.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` is not exercised → the `TypeError` above passes the suite unnoticed.
**Confidence:** High
**Fix:** Add a test for an unknown `giftRecipientId`, asserting the behavior chosen in the fix above (`null` or a thrown error).

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
**Relevant tests:** changed — `test/labels.test.js` adds a test for a valid gift recipient (id 2); the existing tests cover an unknown customer and the plain label. No test covers an unknown `giftRecipientId`. Execution: not run.
**Look first:** `src/labels.js` (unguarded recipient lookup throws a `TypeError`), `test/labels.test.js` (no test for an unknown recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
