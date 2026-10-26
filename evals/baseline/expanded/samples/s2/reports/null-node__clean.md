**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship an order to its gift recipient's address when `giftRecipientId` is set, and return no label when that recipient is unknown (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The new recipient lookup guards against an unknown id: `src/labels.js:14-16` returns `null` instead of dereferencing `recipient.address`.
- The change stays small and fits the file's existing style. The no-gift path still resolves to `customer`, so existing behavior is unchanged.
- `test/labels.test.js:15-24` covers both the success path (gift to a known recipient) and the failure path (unknown recipient). The existing tests still cover the non-gift path.

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

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `test/labels.test.js` adds "ships gifts to the recipient" (known recipient, checks the recipient's name and address) and "returns null for an unknown gift recipient". The existing tests cover the unknown customer and the non-gift label. They do not cover a falsy `giftRecipientId` such as `0`. Execution: not run.
**Look first:** `src/labels.js` (new recipient selection and null guard at lines 13-17), `test/labels.test.js` (new gift tests).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
