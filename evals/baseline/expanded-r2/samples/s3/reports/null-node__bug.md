**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship gift orders to the gift recipient's name and address instead of the buyer's (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and stays in `shippingLabel`. The no-gift path still builds the label from `customer`, so existing orders keep their current output.
- `test/labels.test.js:15-20` adds a test for the new gift path with the exact expected label text.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** `recipient` comes from `customers.get(order.giftRecipientId)`. The result is never checked, although `Map.get` returns `undefined` for an unknown id. The function already returns `null` when `customerId` is unknown, but it has no equivalent guard for the recipient.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined` → line 14 reads `recipient.name` and throws `TypeError: Cannot read properties of undefined`, so label generation for that order crashes. Verification searched the repository for other callers and for validation of `giftRecipientId`. The only callers are the tests, and none covers an unknown recipient. `giftRecipientId` is not validated anywhere in the repository.
**Confidence:** High
**Fix:** Look up the recipient first and apply the same guard as for the customer, for example `if (!recipient) { return null; }`, or throw an explicit error if a missing recipient should be distinguished from a missing customer. Add a test for the unknown-recipient case.

### Tests/Coverage — Suggestion

**Location:** `test/labels.test.js:15-20`
**Issue:** The new test covers only the case where the recipient exists. The test file has a failure-path test for an unknown customer, but nothing for an unknown `giftRecipientId`.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` is not exercised → the crash described above goes unnoticed by the suite.
**Confidence:** High
**Fix:** Add a test for the unknown-recipient case that asserts the behavior chosen for the guard (`null` or a thrown error).

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
**Relevant tests:** changed — `test/labels.test.js` adds a test for shipping to an existing gift recipient. The existing tests cover an unknown customer and the plain label. No test covers an unknown `giftRecipientId`. Execution: not run.
**Look first:** `src/labels.js` (unguarded `recipient` dereference at lines 13-14 can throw), `test/labels.test.js` (no test for an unknown recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
