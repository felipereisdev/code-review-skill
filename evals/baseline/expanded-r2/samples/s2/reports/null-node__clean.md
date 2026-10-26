**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: print the shipping label for a gift order with the gift recipient's name and address instead of the buyer's (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `src/labels.js:13-16` keeps the old behavior when `giftRecipientId` is unset, because `recipient` falls back to `customer`. A missing gift recipient returns `null`, the same way a missing buyer does.
- The two new tests in `test/labels.test.js:15-24` cover the gift path (a valid recipient) and the unknown-recipient path. The existing tests for the non-gift path are unchanged.
- The change is small and fits the existing code.

## Findings

Code review passed — no issues found.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
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
| **Total**             | **0**    | **0**   | **0**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/labels.test.js` adds a gift-recipient label test and an unknown-recipient `null` test, and the existing unknown-customer and plain-label tests still run the non-gift path. Not covered: an order with `giftRecipientId` set but an unknown `customerId`. Execution: not run.
**Look first:** `src/labels.js` (the new recipient lookup and the `null` fallback), `test/labels.test.js` (new gift-path tests).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
