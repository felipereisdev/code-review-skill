# Code Review: staged changes (`src/charge.ts`, `test/charge.test.ts`)

**Stack detected:** TypeScript, Node ESM, Vitest. No framework, Docker, DB or architecture-pattern files apply, so only `typescript.md` was loaded. I did not use the context7 API check because no library API is in question.

## What Was Done Well
- `ChargeResult` is a discriminated union, and the new `{ ok: false, error }` branch already fits it, so the public type did not change.
- The catch narrows `error` with `instanceof Error` and falls back to `String(error)`. That matches the TypeScript rule about narrowing catch variables.
- The new test covers the failure path. It injects a stub gateway and makes no real calls.

## Findings

### Potential Bugs / Security — Warning

**File:** `src/charge.ts:15-17`
**Issue:** The catch block turns every exception into `{ ok: false, error: message }`. The result is the same whether the gateway declined the card, timed out, or hit a bug such as a `TypeError` or a network failure. Callers cannot tell a permanent decline from a transient outage, so they can't decide whether to retry or alert. Programming errors are also silently converted into a "failed charge" value. The raw gateway message is also passed on as `error`. If it reaches an API response or a log, it may expose gateway internals.
**Fix:** Return a stable error code or kind, for example `{ ok: false, code: 'declined' | 'gateway_error', error }`. Log unexpected errors and send them to error reporting, and don't forward their raw messages to end users. Only convert the gateway's expected failures (for example a declined-card error class) to `ok: false`, and rethrow the rest.

### Observability — Warning

**File:** `src/charge.ts:15-17`
**Issue:** The exception is swallowed with no log, metric or error-tracking call. Payment failures will be invisible operationally. The `customerId` and the error context are lost.
**Fix:** Log at `error` or `warn` level with structured fields (customerId, amountCents, error name). Do not log card data. Forward the error to the error-tracking system.

### Resilience — Suggestion

**File:** `src/charge.ts:12-18`
**Issue:** `gateway.charge` has no timeout, retry or idempotency key. Now that failures are returned as values, a caller that retries after `ok: false` could double-charge if the first call actually succeeded but the response was lost (for example on a timeout).
**Fix:** Pass an idempotency key to the gateway and add a timeout. Document whether `ok: false` is safe to retry.

### Tests/Coverage — Suggestion

**File:** `test/charge.test.ts:13-16`
**Issue:** The test covers only an `Error` instance. The `String(error)` branch (a non-`Error` rejection such as a string) is untested. There are also no tests for edge cases such as an invalid `amountCents` (0 or negative).
**Fix:** Add a test with `throw 'boom'` that expects `error: 'boom'`. Consider validating `amountCents` as a positive integer.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          | N/A |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 1       | 0          |     |
| Accessibility         | 0        | 0       | 0          | N/A |
| Observability         | 0        | 1       | 0          |     |
| API Design            | 0        | 0       | 0          | N/A |
| Resilience            | 0        | 0       | 1          |     |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **2**   | **2**      |     |

The security concern about forwarding raw error messages is counted under Potential Bugs rather than as a separate Security finding. There are no blockers.
