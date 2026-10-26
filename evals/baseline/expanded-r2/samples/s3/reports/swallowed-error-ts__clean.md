**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `chargeInvoice` return `{ ok: false, error }` when the payment gateway throws, instead of letting the exception propagate (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The new code uses the `ChargeResult` union that already existed. `{ ok: false; error: string }` was declared but never produced, so the change finishes an existing contract.
- The catch narrows `unknown` with `error instanceof Error` before it reads `.message`. That follows strict TypeScript and avoids an `any` catch variable.
- The change comes with a failure-path test that asserts the exact returned value.

## Findings

### Observability — Suggestion

**Location:** `src/charge.ts:15-17`
**Issue:** The catch block turns the gateway exception into a return value and neither logs nor reports it. The original exception, including its stack, is lost.
**Evidence:** `gateway.charge` throws (network failure, gateway 5xx, programming error) → the function returns `{ ok: false, error: message }` and nothing is written to a log or an error tracker. Unless every caller logs the result, these failures leave no trace.
**Confidence:** High
**Fix:** Log or report the caught error (with its stack and the customer or invoice identifier, but no card data) before returning. Alternatively, add a `cause` to the result.

### Tests/Coverage — Suggestion

**Location:** `test/charge.test.ts:13-16`
**Issue:** The new test covers only a thrown `Error`. The `String(error)` branch at `src/charge.ts:16` has no test.
**Evidence:** A gateway rejects with a non-`Error` value such as a string or an object → `String(error)` runs (an object becomes `"[object Object]"`). No test pins that behavior.
**Confidence:** High
**Fix:** Add a case where the gateway throws a string and assert the resulting `error`. If `"[object Object]"` is not acceptable, change the formatting.

## Needs human verification

### Resilience — Warning

**Location:** `src/charge.ts:12-18`
**Issue:** Every exception from `gateway.charge` now becomes `{ ok: false, error: <message> }`. Charges that were declined, charges that failed because of a transient error, and charges whose outcome is unknown can no longer be told apart. The result carries only a message string, so a caller cannot tell whether it is safe to retry.
**Evidence:** `gateway.charge` times out or loses the connection after the gateway has already captured the payment → `chargeInvoice` returns `{ ok: false, error: 'timeout' }`. A caller that treats `ok: false` as "not charged" and retries, or re-queues the job, then charges the customer twice. Previously the exception propagated and could not be mistaken for a decline. Nothing in this repository calls `chargeInvoice`, and the function takes no idempotency key. A person must check how the callers (in another repository or a later change) handle `ok: false` and retries.
**Confidence:** Medium
**Fix:** Add a machine-readable discriminator to the failure result, for example `kind: 'declined' | 'unknown'`. Rethrow or flag errors whose outcome is unknown. Pass an idempotency key to the gateway for retried charges.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         | 0        | 0       | 0          | N/A |
| Observability         | 0        | 0       | 1          |     |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          |     |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **2**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test/charge.test.ts` covers the success path and a gateway that throws an `Error` (`error: 'card declined'`). It does not cover a non-`Error` throw, a timeout, or the retry behavior. Execution: not run.
**Look first:** `src/charge.ts` (every gateway exception becomes `ok: false`, and an unknown outcome can look like a decline), `test/charge.test.ts` (the `String(error)` branch is untested).
**Ready to merge:** With fixes — a person must check 1 finding under Needs human verification before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/charge.ts`, `test/charge.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/resilience.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:**
- callers of `chargeInvoice` — context not read, not material: the repository has no caller, so how `ok: false` is handled and retried could not be checked. The result type already declared the `ok: false` variant, so the changed behavior itself could be judged.
