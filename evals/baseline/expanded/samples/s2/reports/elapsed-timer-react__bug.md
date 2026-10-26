**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add an elapsed-time counter ("Time: Ns") to `QuizHeader` (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The effect returns a cleanup that calls `clearInterval`, so the timer does not leak on unmount.
- The change adds a test for the new UI, and the component stays small and self-contained.

## Findings

### Potential Bugs — Warning

**Location:** `src/components/QuizHeader.tsx:11`
**Issue:** The interval callback calls `setSeconds(seconds + 1)`. The effect has an empty dependency array, so the callback closes over the first render's `seconds`, which is `0`. The setter never receives the latest value.
**Evidence:** Component mounts with `seconds = 0` → every tick runs `setSeconds(0 + 1)` → the display goes from `Time: 0s` to `Time: 1s` after one second and stays there, so the timer never advances past 1s. Verification checked the effect's dependency array (`[]`) and the `useState(0)` initializer; nothing re-creates the interval with a newer `seconds`. This is not covered by the React precedents, because it is not a StrictMode or batching artifact.
**Confidence:** High
**Fix:** Use a functional update, `setSeconds((s) => s + 1)`, which keeps the empty dependency array correct.

### Tests/Coverage — Suggestion

**Location:** `src/components/QuizHeader.test.tsx:11-14`
**Issue:** The new test only checks the initial `Time: 0s` render. It never advances time, so it does not exercise the counter's behavior.
**Evidence:** The stale-closure bug above leaves the timer stuck at `Time: 1s`, and `starts the timer at zero` still passes, because it never advances time.
**Confidence:** High
**Fix:** Use `vi.useFakeTimers()` and `act(() => vi.advanceTimersByTime(3000))`, then assert `Time: 3s`. Restore real timers afterwards.

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
**Relevant tests:** changed — `src/components/QuizHeader.test.tsx` adds `starts the timer at zero`, which covers only the initial render; it does not cover ticking. Execution: not run.
**Look first:** `src/components/QuizHeader.tsx` (stale closure in `setSeconds(seconds + 1)` freezes the timer at 1s), `src/components/QuizHeader.test.tsx` (no test advances time).
**Ready to merge:** With fixes — 1 Warning finding should be fixed; none blocks the merge.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/QuizHeader.test.tsx`, `src/components/QuizHeader.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Accessibility, Stack-Specific.
**Not verified:** nothing.
