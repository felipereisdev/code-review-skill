**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add an elapsed-seconds timer to the quiz header (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The effect returns a cleanup that calls `clearInterval`, so the timer does not leak when the component unmounts.
- The new test queries by visible text, and the existing test queries by role, so both check what the user sees.
- The change is small and keeps the timer state inside the component that shows it.

## Findings

### Potential Bugs — Warning

**Location:** `src/components/QuizHeader.tsx:10-13`
**Issue:** The interval callback calls `setSeconds(seconds + 1)`, and the effect has an empty dependency array. The callback closes over `seconds` from the first render, which is `0`. The timer therefore never counts past 1.
**Evidence:** `QuizHeader` mounts with `seconds = 0` → every tick runs the same callback, `setSeconds(0 + 1)` → the header shows `Time: 1s` after one second and stays there for as long as the component is mounted. I read the whole component, and nothing else updates `seconds`. Verification found no other caller (`src/` holds only this component and its test). Types and the empty dependency array do not prevent the stale read. The only test checks the initial `0` and never advances time.
**Confidence:** High
**Fix:** Use the functional updater, `setInterval(() => setSeconds((s) => s + 1), 1000)`. The `[]` dependency array is then correct. The alternative is to put `seconds` in the dependency array, which recreates the interval on every tick.

### Tests/Coverage — Suggestion

**Location:** `src/components/QuizHeader.test.tsx:15-18`
**Issue:** The new test only checks the initial text `Time: 0s`. Nothing covers the timer advancing, which is the behavior the change adds.
**Evidence:** The `setSeconds(seconds + 1)` bug above would pass this test, because the `0` render is correct, so the test cannot catch a counter that stops at 1.
**Confidence:** High
**Fix:** Add a test with `vi.useFakeTimers()` that advances time by 3000 ms inside `act`, then asserts `Time: 3s`. Restore real timers afterwards.

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
**Relevant tests:** changed — the new test in `src/components/QuizHeader.test.tsx` checks that the header renders `Time: 0s` at mount; it does not cover the timer advancing. Execution: not run.
**Look first:** `src/components/QuizHeader.tsx` (stale `seconds` in the interval callback; the counter stops at 1), `src/components/QuizHeader.test.tsx` (no test of the timer ticking).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/QuizHeader.test.tsx`, `src/components/QuizHeader.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`, `tsconfig.json`, `vitest.config.ts`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Accessibility, Stack-Specific.
**Not verified:** nothing.
