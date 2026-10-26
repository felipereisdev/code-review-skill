I'm writing up the staged review of `src/charge.ts` and `test/charge.test.ts`. I found no Critical or Warning issues, only two Suggestions.

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `chargeInvoice` return `{ ok: false, error }` when the payment gateway throws, in place of letting the rejection propagate (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change uses the `ChargeResult` discriminated union that already existed, so the `ok: false` variant had a producer and callers can narrow on `ok`.
- The `catch` narrows `error` with `instanceof Error` and falls back to `String(error)`. It doesn't assume the thrown value is an `Error`.
- The change adds a failure-path test that exercises the new branch end to end through a typed `PaymentGateway` stub, with no real I/O.

## Findings

### Resilience — Suggestion

**Location:** `src/charge.ts:15-18`
**Issue:** Every thrown value becomes `{ ok: false, error: <message string> }`. The result carries no error code, no type, and no marker for whether the charge may still have gone through.
**Evidence:** `gateway.charge` times out after the provider has already processed the charge → the function returns `{ ok: false, error: 'timeout' }`, the same shape as a decline → a caller can't tell a retriable or unknown outcome from a final decline, and may retry or report failure without an idempotency key. The code is correct as written. No caller exists in this repository, so I could not confirm any retry behavior.
**Confidence:** High
**Fix:** Add a machine-readable field to the failure variant, for example `code: 'declined' | 'unknown'`, or keep the original error as `cause`. Callers can then separate final declines from indeterminate failures.

### Tests/Coverage — Suggestion

**Location:** `test/charge.test.ts:13-16`
**Issue:** The new test only throws an `Error` instance. The `String(error)` branch at `src/charge.ts:16`, which handles a non-`Error` rejection, is not covered.
**Evidence:** A gateway SDK rejects with a plain string or object → the `String(error)` branch runs (an object yields `[object Object]`) → no test would catch a regression in that branch.
**Confidence:** High
**Fix:** Add a case where the stub throws a non-`Error` value, such as `throw 'boom'`, and assert the resulting `error` string.

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
| Resilience            | 0        | 0       | 1          |     |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **2**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test/charge.test.ts` covers the success path and a gateway that throws an `Error` (`card declined`); it leaves out a non-`Error` rejection. Execution: not run.
**Look first:** `src/charge.ts` (the catch-all that turns every failure into a plain message in a payment flow), `test/charge.test.ts` (the non-`Error` branch is untested).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/charge.ts`, `test/charge.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/privacy.md`, `skill:references/resilience.md`, `skill:stacks/node.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Observability, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
