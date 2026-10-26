**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add an elapsed-time counter, in seconds, to the quiz header (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The `setInterval` effect returns `clearInterval(id)`, so the timer is removed on unmount. The empty dependency array is correct because the effect uses nothing from the render scope.
- The counter updates with the functional form `setSeconds((s) => s + 1)`. That avoids a stale closure, so the effect does not have to re-subscribe on every tick.
- State lives in the component that renders it.
- The change adds a test next to the existing one, in the same style: `render`, then a query by role or text.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/components/QuizHeader.test.tsx:15-18`
**Issue:** The new test only checks the initial render (`Time: 0s`). Nothing exercises the behavior this change adds, which is the counter advancing and the interval being cleared on unmount.
**Evidence:** A regression such as `s + 2`, a 10 ms interval, or removing the `clearInterval` cleanup → `starts the timer at zero` still passes, because it never advances time or unmounts the component.
**Confidence:** High
**Fix:** Use `vi.useFakeTimers()` and `vi.advanceTimersByTime(3000)` inside `act`, then assert `Time: 3s`. Also unmount and assert that `vi.getTimerCount()` is 0. Restore real timers in `afterEach`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
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
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `src/components/QuizHeader.test.tsx` now checks that the initial render shows `Time: 0s`; it does not cover the counter advancing or the cleanup on unmount. Execution: not run.
**Look first:** `src/components/QuizHeader.tsx` (new interval effect and its cleanup), `src/components/QuizHeader.test.tsx` (the test covers only the initial state).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/QuizHeader.test.tsx`, `src/components/QuizHeader.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Stack-Specific.
**Not verified:** nothing.
