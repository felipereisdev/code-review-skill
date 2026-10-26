**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add an elapsed-time counter, in seconds, to the quiz header (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The interval is cleared in the effect's cleanup function, so the timer does not leak after unmount.
- The change comes with a test, and it uses `getByText` to check the rendered output.
- The change is small and keeps the timer state inside the component that shows it.

## Findings

### Potential Bugs — Warning

**Location:** `src/components/QuizHeader.tsx:11-13`
**Issue:** The interval callback calls `setSeconds(seconds + 1)`, but the effect has an empty dependency array (`[]`). The callback closes over the `seconds` value from the first render, which is `0`.
**Evidence:** `QuizHeader` mounts → the effect runs once and the interval captures `seconds === 0` → every tick calls `setSeconds(0 + 1)` → the display goes to `Time: 1s` after the first second and stays there. The timer never goes past 1 second. Verification found no other caller or guard that changes this. The only test checks the initial `0` and never advances time, so no existing test catches it. The repository has no ESLint config, so `react-hooks/exhaustive-deps` is not enforcing the dependency list.
**Confidence:** High
**Fix:** Use a functional update, so the effect does not depend on `seconds`: `setInterval(() => setSeconds((s) => s + 1), 1000)`.

### Tests/Coverage — Suggestion

**Location:** `src/components/QuizHeader.test.tsx:11-14`
**Issue:** The new test only checks the initial render (`Time: 0s`). It does not check that the timer advances.
**Evidence:** Trigger → effect: the stale-closure bug above leaves the timer stuck at `Time: 1s`, and this test still passes because it never advances time.
**Confidence:** High
**Fix:** Add a test with `vi.useFakeTimers()` that wraps `vi.advanceTimersByTime(3000)` in `act(...)` and expects `Time: 3s`.

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
**Relevant tests:** changed — `src/components/QuizHeader.test.tsx` covers the title heading and the initial `Time: 0s` render, but not the timer advancing. Execution: not run.
**Look first:** `src/components/QuizHeader.tsx` (stale `seconds` closure in the interval callback, so the timer stops at 1s), `src/components/QuizHeader.test.tsx` (no test that the timer advances).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/QuizHeader.test.tsx`, `src/components/QuizHeader.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Stack-Specific.
**Not verified:** nothing.
