**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: print the shipping label with the gift recipient's name and address when an order has a `giftRecipientId` (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change is small and sits in the one function that builds the label. Orders without `giftRecipientId` still use the ordering customer, so the existing `formats the label` test still describes their behavior.
- The change comes with a test for the new gift path. It asserts the full three-line label, not just one field.

## Findings

### Potential Bugs — Critical

**Location:** `src/labels.js:13-14`
**Issue:** `recipient` is looked up with `customers.get(order.giftRecipientId)` and used without a null check. The function already returns `null` when the ordering customer is unknown, but it has no equivalent guard for an unknown recipient.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` → `customers.get(99)` returns `undefined` → line 14 evaluates `recipient.name` and throws `TypeError: Cannot read properties of undefined (reading 'name')`, so label generation crashes for that order. Verification searched the repository for callers and other uses of `giftRecipientId` and found none. The only guard is the `customer` check on lines 10-12, which covers `customerId` and not the recipient. No existing test covers an unknown recipient.
**Confidence:** High
**Fix:** After the lookup, return `null` when `recipient` is missing, as the function already does for an unknown customer. For example: `if (!recipient) { return null; }`. Alternatively, fall back to `customer` or throw an explicit, descriptive error, whichever the callers expect.

### Tests/Coverage — Suggestion

**Location:** `test/labels.test.js:15-20`
**Issue:** The new test covers only a valid gift recipient. It has no case for a `giftRecipientId` that is not in `customers`, which is the case that crashes in `src/labels.js:14`.
**Evidence:** `shippingLabel({ customerId: 1, giftRecipientId: 99 })` is never exercised → the `TypeError` above would not be caught by the suite.
**Confidence:** High
**Fix:** Add a test for an unknown `giftRecipientId` that asserts the behavior chosen for the fix, for example `null`, next to the existing `returns null for an unknown customer` test.

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
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient`, which runs the new branch with a valid recipient id and checks the full label. It leaves out an unknown `giftRecipientId`. Execution: not run.
**Look first:** `src/labels.js` (Critical: unknown gift recipient makes line 14 throw a `TypeError`), `test/labels.test.js` (no test for an unknown recipient).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
