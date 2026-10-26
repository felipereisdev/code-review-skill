**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `chargeInvoice` return a result instead of throwing when the payment gateway fails (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `ChargeResult` is already a discriminated union with an `ok: false` variant, so the failure case has a typed shape ready.
- The change adds a test for the gateway-failure path instead of only the happy path.

## Findings

### Potential Bugs — Critical

**Location:** `src/charge.ts:15-17`
**Issue:** The `catch` block turns every gateway failure into a success result, `{ ok: true, chargeId: '' }`. The existing `{ ok: false; error: string }` variant is never returned.
**Evidence:** `gateway.charge(...)` throws (card declined, network error, timeout) → `chargeInvoice` resolves `{ ok: true, chargeId: '' }` → any caller that trusts `ok: true`, as the type contract invites, treats the invoice as paid with an empty charge id. No money was collected, and the failed payment cannot be distinguished from a real one. The error is also discarded without being logged, so nothing records that the charge failed. Verification found no caller in the repository (`git ls-files` lists only `src/charge.ts` and `test/charge.test.ts`), so nothing guards or contradicts this path.
**Confidence:** High
**Fix:** Return the failure in the declared shape, `return { ok: false, error: err instanceof Error ? err.message : 'charge failed' }`, with `catch (err: unknown)`. Log or report the original error. Rethrow errors that are not gateway declines, so a bug is not reported as a payment failure.

### Tests/Coverage — Suggestion

**Location:** `test/charge.test.ts:13-16`
**Issue:** The new test only asserts that the promise resolves to something (`toBeDefined()`). It never checks `ok` or `error`.
**Evidence:** The `failing` gateway throws `card declined` → the test passes with the current code, which returns `ok: true`, and it would also pass with the correct `ok: false` result. It cannot catch the bug above, and its name ("does not throw") describes the wrong behavior as the goal.
**Confidence:** High
**Fix:** Assert the failure result, for example `resolves.toEqual({ ok: false, error: 'card declined' })`, and rename the test to say it reports the failure.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 0          |     |
| Accessibility         |          |         |            | N/A |
| Observability         | 0        | 0       | 0          |     |
| API Design            |          |         |            | N/A |
| Resilience            | 0        | 0       | 0          |     |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test/charge.test.ts` covers the success path (`ch_123`) and a throwing gateway, but only asserts that the result is defined, not its `ok` or `error` values. Execution: not run.
**Look first:** `src/charge.ts` (failed charges are returned as `ok: true`), `test/charge.test.ts` (the failure test cannot catch that).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/charge.ts`, `test/charge.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/resilience.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Observability, Resilience, Stack-Specific.
**Not verified:** nothing.
