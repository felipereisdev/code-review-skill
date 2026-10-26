**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship an order to a separate gift recipient when `giftRecipientId` is set (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and does one thing. A new test, `ships gifts to the recipient`, covers the gift path through `shippingLabel`.
- The existing `null` guard for an unknown buyer (`src/labels.js:10-12`) runs before the new branch, and its test is kept.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** `recipient` comes from `customers.get(order.giftRecipientId)` with no check that the lookup found anyone. The next line reads `recipient.name` and `recipient.address.street`.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined` → `recipient.name` throws a `TypeError` and label generation fails. The old code returned `null` for an unknown customer, so this crash is new. Verification read `src/labels.js` and `test/labels.test.js`. The function has no other guard, no other caller exists in the repository, and no test covers an unknown recipient.
**Confidence:** High
**Fix:** Look up the recipient first and return `null` (or throw a clear domain error) when it is missing, for example `const recipient = order.giftRecipientId ? customers.get(order.giftRecipientId) : customer; if (!recipient) return null;`. Keep whichever behaviour the callers expect for an unknown customer.

### Tests/Coverage — Suggestion

**Location:** `test/labels.test.js:15-20`
**Issue:** The new test covers only a valid gift recipient. Nothing covers a `giftRecipientId` that does not exist.
**Evidence:** The unknown-recipient case in the finding above has no test, so the `TypeError` would not be caught by the suite.
**Confidence:** High
**Fix:** Add a test for `shippingLabel({ customerId: 1, giftRecipientId: 99 })` that asserts the chosen behaviour, such as `null`.

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
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient` (valid recipient) beside the existing unknown-customer and normal-label tests. It leaves out an unknown `giftRecipientId`. Execution: not run.
**Look first:** `src/labels.js` (Critical: unguarded `recipient` lookup at lines 13-14), `test/labels.test.js` (no test for an unknown recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
