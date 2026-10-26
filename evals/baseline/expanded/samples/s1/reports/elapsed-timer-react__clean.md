Reviewing the staged change to `QuizHeader` and its test. Nothing was modified and the tests were not run, because `node_modules` isn't installed. The full report follows.

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add an elapsed-seconds timer to `QuizHeader` that starts at 0 and ticks every second, with a test for its initial value (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The `setInterval` in `src/components/QuizHeader.tsx` is cleared in the effect's cleanup function, and the dependency array is `[]`, which is correct because the effect uses no outer values.
- The tick uses the functional updater `setSeconds((s) => s + 1)`, so there is no stale-closure bug.
- `aria-live="off"` keeps a screen reader from announcing the timer every second.
- The change comes with a test.

## Findings

### Tests/Coverage — Suggestion

**Location:** `src/components/QuizHeader.tsx:9-12`
**Issue:** The new tick and cleanup behavior has no test. The only added test checks the initial `Time: 0s` text.
**Evidence:** The interval callback is changed to `s + 2`, or `clearInterval(id)` is removed from the cleanup → the added test still passes, because it never advances time or unmounts. A leaked timer or a wrong increment would go unnoticed.
**Confidence:** High
**Fix:** Add a test with `vi.useFakeTimers()` that advances 3000 ms (inside `act`) and expects `Time: 3s`. Add another that unmounts the component and checks that `vi.getTimerCount()` is 0.

## Needs human verification

### Tests/Coverage — Warning

**Location:** `src/components/QuizHeader.test.tsx:11-14`
**Issue:** The new test may fail, because DOM cleanup between tests may not run. `vitest.config.ts` sets only `environment: 'jsdom'` and does not set `globals: true`. `@testing-library/react` registers its automatic `afterEach(cleanup)` only when `afterEach` is a global. Without it, the first test's render stays in `document.body`.
**Evidence:** The first test renders `<QuizHeader title="Capitals" />` and finishes at about 0 s, so its `<p>Time: 0s</p>` is still mounted → the second test renders another header and `screen.getByText('Time: 0s')` finds two matches. It throws "Found multiple elements" and the test fails. Before this change the first test passed with a single render, so the leftover DOM was harmless. The added test is the first one to expose it. I read the repository files, but `@testing-library/react` is not installed, so I could not confirm the auto-cleanup condition in its source. I did not run the test.
**Confidence:** Medium. A person must check by running `npm test`, or by reading the auto-cleanup condition in the installed `@testing-library/react` 16.x.
**Fix:** Set `globals: true` in `vitest.config.ts` so auto-cleanup registers. Alternatively, call `afterEach(cleanup)` explicitly in the test file, or import `cleanup` and run it in an `afterEach`.

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
**Relevant tests:** changed — `QuizHeader.test.tsx` covers the title heading and the initial `Time: 0s` text. It does not cover ticking, the interval cleanup on unmount, or isolation between tests (see Needs human verification). Execution: not run.
**Look first:** `src/components/QuizHeader.test.tsx` (the new test may fail from DOM left over by the first test), `src/components/QuizHeader.tsx` (the timer logic has no test).
**Ready to merge:** With fixes — a person must check 1 finding under Needs human verification before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/components/QuizHeader.test.tsx`, `src/components/QuizHeader.tsx`.
**Read for context:** `package.json`, `skill:references/accessibility.md`, `skill:references/intent.md`, `skill:stacks/react.md`, `skill:stacks/typescript.md`, `tsconfig.json`, `vitest.config.ts`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Accessibility, Stack-Specific.
**Not verified:**
- `@testing-library/react` auto-cleanup behavior under Vitest without `globals` — API not validated, not material: no documentation tool was available and the library is not installed. Every behavior of the changed component was judged without it. Only whether the added test passes depends on it.
- `@testing-library/react` source (auto-cleanup registration) — context not read, not material: the repository has no `node_modules`, so I could not inspect it. The component's behavior was judged from the code I read.
