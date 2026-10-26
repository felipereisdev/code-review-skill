**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add an elapsed-seconds timer to the quiz header (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The interval is cleared in the effect's cleanup function, so the timer does not leak when the component unmounts.
- The change adds a test for the new timer text, and the `<p>` is a plain semantic element.

## Findings

### Potential Bugs — Warning

**Location:** `src/components/QuizHeader.tsx:10-13`
**Issue:** The interval callback calls `setSeconds(seconds + 1)` inside an effect whose dependency array is `[]`. The callback closes over the `seconds` value from the first render, which is `0`.
**Evidence:** The component mounts with `seconds = 0` → every tick runs `setSeconds(0 + 1)` → the display goes to `Time: 1s` after one second and stays there instead of counting up. Verification checked the only caller (the test file) and found no ESLint or `react-hooks/exhaustive-deps` setup in the repo to flag it. The only new test asserts the initial `Time: 0s` and never advances time.
**Confidence:** High
**Fix:** Use the functional updater so the effect does not depend on `seconds`: `setInterval(() => setSeconds((s) => s + 1), 1000)`.

### Tests/Coverage — Suggestion

**Location:** `src/components/QuizHeader.test.tsx:11-14`
**Issue:** The new test only checks the initial `Time: 0s` render. It never advances the timer, so it cannot catch a timer that does not count up.
**Evidence:** With the stale-closure bug above, `render(<QuizHeader title="Capitals" />)` still shows `Time: 0s` and the test passes, while the displayed time is stuck at 1s after the first tick.
**Confidence:** High
**Fix:** Use `vi.useFakeTimers()` and `act(() => vi.advanceTimersByTime(3000))`, then assert `Time: 3s`. Also assert that unmounting clears the interval.

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
**Relevant tests:** changed — `QuizHeader.test.tsx` adds a test of the initial `Time: 0s` render and keeps the title test; neither advances the timer or checks the interval cleanup. Execution: not run.
**Look first:** `src/components/QuizHeader.tsx` (stale `seconds` closure in the interval effect, Warning), `src/components/QuizHeader.test.tsx` (the new test cannot detect the timer bug).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/QuizHeader.test.tsx`, `src/components/QuizHeader.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`, `tsconfig.json`, `vitest.config.ts`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Accessibility, Stack-Specific.
**Not verified:** nothing.
