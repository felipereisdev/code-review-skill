**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add a running seconds timer, shown as "Time: Ns", to the `QuizHeader` component (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The interval is cleared in the effect's cleanup function, so the timer does not leak when the component unmounts.
- A test was added for the initial timer display, next to the existing heading test.

## Findings

### Potential Bugs — Warning

**Location:** `src/components/QuizHeader.tsx:10-13`
**Issue:** The interval callback calls `setSeconds(seconds + 1)`, and the effect has an empty dependency array. The callback therefore keeps the `seconds` value from the first render (0) for as long as the component is mounted.
**Evidence:** `QuizHeader` mounts → the effect runs once with `seconds === 0` → every tick calls `setSeconds(0 + 1)` → the display goes from "Time: 0s" to "Time: 1s" after one second and stays at "Time: 1s" forever. The timer never counts past 1. I found no `eslint` config in the repository, so no linter reports this (`react-hooks/exhaustive-deps` is not configured).
**Confidence:** High
**Fix:** Use a functional update, `setInterval(() => setSeconds((s) => s + 1), 1000)`. The empty dependency array is then correct.

### Tests/Coverage — Suggestion

**Location:** `src/components/QuizHeader.test.tsx:15-18`
**Issue:** The new test only checks the initial "Time: 0s" text. Nothing tests that the timer advances or that the interval is cleared on unmount.
**Evidence:** The stale-closure bug above (timer stuck at 1s) passes this test unchanged, because the test never advances time. A test using `vi.useFakeTimers()` and `vi.advanceTimersByTime(3000)` that expects "Time: 3s" would have caught it.
**Confidence:** High
**Fix:** Add a fake-timer test that advances time by several seconds and asserts the displayed value. Optionally add an unmount test that asserts the interval is cleared.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 1       | 0          |     |
| Accessibility         | 0        | 0       | 0          |     |
| Observability         |          |         |            | N/A |
| API Design            |          |         |            | N/A |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **1**   | **1**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `QuizHeader.test.tsx` renders the component and checks the heading and the initial "Time: 0s" text. It does not cover the timer advancing or the cleanup on unmount. Execution: not run.
**Look first:** `src/components/QuizHeader.tsx` (stale `seconds` closure in the interval, so the timer stops at 1s), `src/components/QuizHeader.test.tsx` (no test that the timer advances).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/QuizHeader.test.tsx`, `src/components/QuizHeader.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`, `tsconfig.json`, `vitest.config.ts`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Accessibility, Stack-Specific.
**Not verified:** nothing.
