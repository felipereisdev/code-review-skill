**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `chargeInvoice` return `{ ok: false, error }` when the gateway throws, instead of letting the exception propagate (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `src/charge.ts:12-18` uses the `ChargeResult` union that already had an `ok: false` variant, so the new failure path fits the declared contract.
- `src/charge.ts:16` narrows the caught value with `error instanceof Error` before reading `.message`, and falls back to `String(error)`. This matches the TypeScript rule that `catch` values be narrowed.
- `test/charge.test.ts:13-16` adds a failure-path test next to the existing success test.

## Findings

### Tests/Coverage — Suggestion

**Location:** `test/charge.test.ts:13-16`
**Issue:** The new test only covers a gateway that throws an `Error`. The `String(error)` branch at `src/charge.ts:16` (a non-`Error` rejection) is not covered.
**Evidence:** A gateway that rejects with a plain string or an object, for example `throw 'timeout'`, takes the untested branch. A change to that line, such as dropping the `String(...)` call, would not fail any test.
**Confidence:** High
**Fix:** Add a case where `charge` rejects with a non-`Error` value, for example `throw 'boom'`, and assert `{ ok: false, error: 'boom' }`.

## Needs human verification

### Resilience — Warning

**Location:** `src/charge.ts:15-18`
**Issue:** Every thrown error becomes the same `{ ok: false, error: <message> }`. A definitive decline ("card declined") looks the same as an ambiguous failure such as a timeout or a dropped connection, where the charge may already have been committed. Nothing in the result lets a caller tell them apart, and `gateway.charge` is called without an idempotency key.
**Evidence:** `gateway.charge` times out after the provider has captured the payment → `chargeInvoice` returns `{ ok: false, error: 'timeout' }` → a caller that treats `ok: false` as "not paid" and retries, or marks the invoice unpaid, charges the customer twice. Before this change the exception propagated, so a caller could tell "threw" from "declined". Verification searched the repository for callers of `chargeInvoice`; none exist, so whether any caller retries on `ok: false` cannot be checked. Whether the gateway client applies its own idempotency is not visible either. A person must check the consumers of `ChargeResult` and the gateway implementation.
**Confidence:** Medium
**Fix:** Separate decline errors from indeterminate ones in the result, for example `{ ok: false, retryable: boolean, error }`, or rethrow non-decline errors. Pass an idempotency key to `gateway.charge` so retries are safe.

### Observability — Warning

**Location:** `src/charge.ts:15-18`
**Issue:** The catch block drops the original error object (its type, stack and `cause`) and keeps only `message`. It logs nothing and reports nothing to an error tracker.
**Evidence:** A bug or an outage in the gateway client, such as a `TypeError` or a 5xx wrapped in an error → `chargeInvoice` returns `{ ok: false, error: "Cannot read properties of undefined" }`. Unless the caller logs it, no log or alert shows it, and it looks like an ordinary failed payment. Verification found no logger or error-reporting setup in the repository (only `package.json`, `tsconfig.json`, `src/charge.ts` and the tests) and no callers, so whether anything records it upstream cannot be checked. A person must check how the consumers handle `ok: false`.
**Confidence:** Medium
**Fix:** Log the full error with the customer and charge context, without card data, or report it to the error tracker before returning. Only convert expected gateway decline errors into `ok: false`.

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
| Observability         | 0        | 0       | 0          |     |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 0          |     |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 2 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test/charge.test.ts` covers the success path and a gateway that throws an `Error` (`ok: false` with the message); it does not cover non-`Error` rejections, timeouts or retry behavior. Execution: not run.
**Look first:** `src/charge.ts` (the catch block turns every gateway failure into one `ok: false` result in a payment flow), `test/charge.test.ts` (the non-`Error` branch is untested).
**Ready to merge:** With fixes — a person must check 2 findings under Needs human verification before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/charge.ts`, `test/charge.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/resilience.md`, `skill:stacks/node.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Stack-Specific.
**Not verified:**
- callers of `chargeInvoice` — context not read, not material: the repository has no code that calls `chargeInvoice` or consumes `ChargeResult`, so how consumers handle `ok: false` is under Needs human verification. Every changed behavior in the diff could be judged without it.
