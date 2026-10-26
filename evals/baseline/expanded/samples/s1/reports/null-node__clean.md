**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: ship a gift order's label to the gift recipient instead of the buyer (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The lookup for the recipient is guarded. An unknown `giftRecipientId` returns `null`, the same as an unknown customer, so a missing recipient cannot throw at `recipient.address.street`.
- Orders without `giftRecipientId` fall back to the buyer, so the existing label output is unchanged. The existing `formats the label` test still covers that path.
- The change comes with two new tests, one for the gift-recipient label and one for an unknown recipient. They use the existing fixture customers and the project's `node:test` setup.

## Findings

**Code review passed — no issues found.**

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
**Relevant tests:** changed — `test/labels.test.js` adds `ships gifts to the recipient` (label built from the recipient's name and address) and `returns null for an unknown gift recipient`. The existing `formats the label` and `returns null for an unknown customer` still cover the non-gift paths. They do not cover an unknown buyer combined with a gift recipient, or a falsy `giftRecipientId` such as `0`. Execution: not run.
**Look first:** `src/labels.js` (the recipient lookup and fallback logic at lines 13-17), `test/labels.test.js` (new gift cases at lines 15-24).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/labels.js`, `test/labels.test.js`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/node.md`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
