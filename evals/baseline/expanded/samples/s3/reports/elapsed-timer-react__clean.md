## Review report

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add an elapsed-seconds timer to the quiz header (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The `setInterval` is cleared in the effect's cleanup function, so the timer doesn't leak when the component unmounts.
- The counter uses the functional update `setSeconds((s) => s + 1)`, so it doesn't read stale state from the closure.
- The state sits in the component that uses it, and the effect has an empty dependency array, which is correct because it uses no outside values.
- The change comes with a test for the new UI.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/components/QuizHeader.tsx:8-12`
**Issue:** The new interval effect, which increments the counter and clears the timer on unmount, has no test. The only new test checks the initial `Time: 0s`.
**Evidence:** Someone changes `s + 1` to `s`, or deletes `clearInterval(id)` → every test in `QuizHeader.test.tsx` still passes, because none advances time or unmounts the component.
**Confidence:** High
**Fix:** Add a test that uses `vi.useFakeTimers()`, advances time with `vi.advanceTimersByTime(3000)` inside `act`, and expects `Time: 3s`. Add another test that unmounts the component and checks that no interval is left running.

## Needs human verification

### Tests/Coverage — Warning

**Location:** `src/components/QuizHeader.test.tsx:11-14`
**Issue:** The new test may fail with "multiple elements found" because the repository has no test cleanup between tests. `vitest.config.ts` sets only `environment: 'jsdom'`. It has no `globals: true` and no `setupFiles`. The test file imports `describe`, `expect` and `it` explicitly from `vitest`, and no file in the repository calls `cleanup`.
**Evidence:** Testing Library registers its automatic `afterEach(cleanup)` only when a global `afterEach` exists, and under Vitest that requires `globals: true`. If that holds, the first test's render (`shows the quiz title`) stays in `document.body`. The second test's `render` then adds a second header, and `screen.getByText('Time: 0s')` finds two matching `<p>` elements and throws. A person must check this by running `vitest run`, or by confirming how `@testing-library/react@^16` behaves without globals. I could not run tests and `node_modules` is absent.
**Confidence:** Medium
**Fix:** Call `afterEach(cleanup)` in the test file or in a `setupFiles` entry. Alternatively, set `globals: true` in `vitest.config.ts`. Or use the `render` result's own queries, such as `const { getByText } = render(...)`, which are scoped to that render's container.

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
| Observability         |          |         |            | N/A |
| API Design            |          |         |            | N/A |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 1/5 — up to 50 changed lines in 2 files; no risk area.
**Relevant tests:** changed — `src/components/QuizHeader.test.tsx` covers the heading and the initial `Time: 0s`. It doesn't cover the tick or the cleanup on unmount. Execution: not run.
**Look first:** `src/components/QuizHeader.test.tsx` (the new test may fail without cleanup between tests), `src/components/QuizHeader.tsx` (the new interval effect has no test).
**Ready to merge:** No — not fully reviewed (API not validated): whether `@testing-library/react@^16` cleans up automatically under Vitest without `globals`, which decides whether the new test passes.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/QuizHeader.test.tsx`, `src/components/QuizHeader.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`, `tsconfig.json`, `vitest.config.ts`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Stack-Specific.
**Not verified:**
- Testing Library automatic cleanup under Vitest without `globals` — API not validated, material: no documentation tool was available, and `node_modules` is absent, so the new test's pass or fail could not be settled.
