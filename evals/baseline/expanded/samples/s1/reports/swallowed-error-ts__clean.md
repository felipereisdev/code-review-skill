**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `chargeInvoice` return a `{ ok: false, error }` result when the payment gateway fails, instead of letting the exception propagate (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `ChargeResult` is a discriminated union, so callers must narrow on `ok` before reading `chargeId` or `error`. `src/charge.ts:5`
- The catch narrows `unknown` with `instanceof Error` and has a fallback for non-Error throws, which matches the TypeScript catch-clause guidance.
- The change adds a test for the new failure path next to the existing success test.

## Findings

### Tests/Coverage — Suggestion

**Location:** `test/charge.test.ts:13-16`
**Issue:** The new test covers only the `Error` branch of `error instanceof Error ? error.message : String(error)`. The `String(error)` fallback at `src/charge.ts:16` has no test.
**Evidence:** A gateway SDK rejects with a plain string or object, for example `throw 'timeout'` → the fallback runs and nothing asserts its output, so a later edit to that line would go unnoticed.
**Confidence:** High
**Fix:** Add a test whose gateway throws a non-Error value, such as a string, and assert the resulting `{ ok: false, error: '...' }`.

## Needs human verification

### Resilience — Warning

**Location:** `src/charge.ts:12-18`
**Issue:** Every gateway failure is now turned into `{ ok: false, error: <message string> }`. The result keeps no error type or code, no retriable-or-not signal, and no outcome-unknown state, and nothing is logged or reported in this function.
**Evidence:** `gateway.charge` times out or drops the connection after the gateway has already created the charge → the function returns `{ ok: false, error: 'timeout' }`, which looks the same as `{ ok: false, error: 'card declined' }` → a caller that retries on `ok: false` charges the customer twice, because no idempotency key is passed. Before the change the exception reached the caller as a distinct failure. A caller that shows `error` to the end user would also expose raw gateway messages. A person must check this against the callers of `chargeInvoice`.
**Confidence:** Medium
**Fix:** Return a structured error, for example `{ ok: false, code, retriable, message }`, or rethrow the errors where the outcome is unknown. Pass an idempotency key to `gateway.charge` so retries are safe. Log or report the original error before converting it.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
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
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.
**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test/charge.test.ts` covers the success path and a gateway that throws an `Error` ("card declined"). It does not cover a non-Error throw, timeouts or retry behavior. Execution: not run.
**Look first:** `src/charge.ts` (catch-all that turns every gateway failure, including ambiguous ones, into a plain `ok: false` string in a payment flow), `test/charge.test.ts` (the `String(error)` branch is untested).
**Ready to merge:** With fixes — a person must check 1 finding under Needs human verification before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/charge.ts`, `test/charge.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/resilience.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:**
- callers of `chargeInvoice` — context not read, not material: the repository has no caller of `chargeInvoice`, so how callers treat `ok: false` (retry, display) could not be checked. The changed behavior itself was fully judged.
