**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship a gift order's label to the gift recipient instead of the ordering customer (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `shippingLabel` still returns `null` for an unknown customer, and the new `recipient` guard returns `null` for an unknown gift recipient. Neither case throws on `recipient.address`.
- Orders with no `giftRecipientId` still use the ordering customer. The existing `formats the label` test covers this and needs no change.
- The two new tests cover the success path (`ships gifts to the recipient`) and the failure path (`returns null for an unknown gift recipient`) of the new branch.

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
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient` (customer 1 with recipient 2 gives the recipient's label) and `returns null for an unknown gift recipient` (recipient 99). Together with the existing `returns null for an unknown customer` and `formats the label`, they cover every branch of `shippingLabel`. They leave out an order whose `giftRecipientId` is falsy, such as `0`. Execution: not run.
**Look first:** `src/labels.js` (the only behavior change: recipient lookup and null guard), `test/labels.test.js` (tests for the new branch).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:** nothing.
