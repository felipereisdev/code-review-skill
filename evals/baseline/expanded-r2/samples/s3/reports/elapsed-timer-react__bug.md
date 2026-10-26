**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add an elapsed-time counter, in seconds, to `QuizHeader` (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The `useEffect` returns a cleanup that calls `clearInterval`, so the timer does not leak on unmount.
- The change comes with a test for the initial state, in the existing `describe('QuizHeader')` block and using the same `render`/`screen` style as the sibling test.

## Findings

### Potential Bugs — Warning

**Location:** `src/components/QuizHeader.tsx:10-13`
**Issue:** The interval callback calls `setSeconds(seconds + 1)`, but the effect has an empty dependency array. The callback therefore closes over `seconds` from the first render, which is always `0`.
**Evidence:** Mount `<QuizHeader title="Capitals" />` → the effect runs once and its callback captures `seconds = 0` → every tick calls `setSeconds(0 + 1)` → the display goes to `Time: 1s` after one second and stays there, instead of counting 2s, 3s and so on. Verification checked the whole component: `seconds` is only read at `QuizHeader.tsx:11`, and the project has no lint configuration that enforces `react-hooks/exhaustive-deps` (`package.json` has no ESLint), so nothing else catches or prevents it.
**Confidence:** High
**Fix:** Use the functional updater so the callback does not depend on a captured value: `setInterval(() => setSeconds((s) => s + 1), 1000)`. The empty dependency array is then correct.

### Tests/Coverage — Suggestion

**Location:** `src/components/QuizHeader.test.tsx:14-18`
**Issue:** The new test only asserts the initial `Time: 0s` text. It never advances time, so it cannot detect that the counter does not increment.
**Evidence:** The stale-closure bug above leaves the display stuck at `Time: 1s` → this test still passes, because it only checks the state before any tick.
**Confidence:** High
**Fix:** Add a test that uses `vi.useFakeTimers()` and `act(() => vi.advanceTimersByTime(3000))`, then asserts `Time: 3s`. Restore real timers afterwards.

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
| Observability         | 0        | 0       | 0          | N/A |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **1**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `src/components/QuizHeader.test.tsx` adds a test of the initial `Time: 0s` render; it does not cover the counter incrementing. Execution: not run.
**Look first:** `src/components/QuizHeader.tsx` (stale `seconds` closure keeps the timer stuck at 1s), `src/components/QuizHeader.test.tsx` (no test advances the timer).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/QuizHeader.test.tsx`, `src/components/QuizHeader.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`, `tsconfig.json`, `vitest.config.ts`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Accessibility, Stack-Specific.
**Not verified:** nothing.
