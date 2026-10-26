**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship an order to its gift recipient's name and address when `giftRecipientId` is set (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and focused. It keeps the existing `customer` guard and falls back to the buyer when there is no gift recipient, so orders without a gift behave as before.
- It adds a test for the gift path, and the earlier tests for the unknown customer and the plain label still cover the other branches.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** `recipient` comes from `customers.get(order.giftRecipientId)` and is never checked. The existing guard only covers `customer`, the buyer. If the recipient id is not in the map, `recipient` is `undefined`.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → the buyer exists, so the guard on line 10 passes. `customers.get(99)` returns `undefined`, and `recipient.name` on line 14 throws `TypeError: Cannot read properties of undefined (reading 'name')`, so label generation for that order crashes. Verification checked `src/labels.js` and `test/labels.test.js`, the only users of `shippingLabel` in the repository. Nothing validates `giftRecipientId` before the call, and no test covers an unknown recipient.
**Confidence:** High
**Fix:** Look the recipient up first and return `null` when it is missing, as is done for an unknown customer. For example, `if (!recipient) return null;` before building the label. Alternatively, throw an explicit error that names the missing recipient id.

### Tests/Coverage — Suggestion

**Location:** `test/labels.test.js:15-20`
**Issue:** The new test covers only a valid gift recipient. Nothing exercises a `giftRecipientId` that is not in `customers`, the case that crashes.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` is not tested → the `TypeError` above goes unnoticed by the suite.
**Confidence:** High
**Fix:** Add a test for an unknown `giftRecipientId` that asserts the behavior chosen for that case (`null` or a specific error).

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
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient`, which covers a valid `giftRecipientId`. The existing tests cover the unknown customer and the plain label. Nothing covers an unknown `giftRecipientId`. Execution: not run.
**Look first:** `src/labels.js` (Critical: an unknown `giftRecipientId` throws a `TypeError`), `test/labels.test.js` (no test for the unknown recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
