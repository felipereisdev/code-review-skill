**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship a gift order to the gift recipient's name and address instead of the purchaser's, and return `null` when the recipient is unknown (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `src/labels.js:13-16` keeps the existing path for orders without a gift recipient. The `recipient` fallback is `customer`, so the old behavior is unchanged.
- An unknown gift recipient returns `null`, the same as an unknown customer. It does not throw on `recipient.address`.
- `test/labels.test.js:15-24` covers both new branches: a valid gift recipient and an unknown one. The original tests still cover the non-gift path.

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
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **0**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `test/labels.test.js` adds "ships gifts to the recipient" (valid `giftRecipientId` gives the recipient's label) and "returns null for an unknown gift recipient" (`giftRecipientId: 99` gives `null`). The existing tests cover the non-gift label and the unknown customer. No test covers a gift order whose purchaser is unknown. Execution: not run.
**Look first:** `src/labels.js` (the only behavior change: recipient selection and the new null guard), `test/labels.test.js` (new gift-path tests).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
