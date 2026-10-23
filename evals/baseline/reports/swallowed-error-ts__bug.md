# Code Review: staged changes (`src/charge.ts`, `test/charge.test.ts`)

**Stack:** TypeScript (ESM), Vitest, with no framework. I applied the generic rules and `stacks/typescript.md`. No architecture pattern files apply.

## What Was Done Well
- The change is small and easy to follow.
- The `ChargeResult` discriminated union already has an `{ ok: false; error: string }` variant. The correct failure path exists in the type.
- `PaymentGateway` is injected, so the function is easy to test with a fake gateway.

## Findings

### Potential Bugs — Critical

**File:** `src/charge.ts:15`
**Issue:** The bare `catch` returns `{ ok: true, chargeId: '' }` for any gateway failure, including declined cards, network errors and timeouts. Callers will treat the invoice as paid when no charge happened. That is a billing-integrity bug, because invoices can be marked paid with no money collected. The error is also discarded, so nothing records that the failure occurred. The code ignores the `{ ok: false, error }` variant that the type already defines.
**Fix:** Return the failure variant, or let the error propagate:
```ts
} catch (e: unknown) {
  return { ok: false, error: e instanceof Error ? e.message : 'charge failed' };
}
```
Only catch errors you can handle meaningfully. Distinguish declines (return `ok: false`) from unexpected or transient errors (log them and rethrow, or retry safely).

### Tests/Coverage — Critical

**File:** `test/charge.test.ts:13-16`
**Issue:** The new test only asserts `resolves.toBeDefined()`. It passes with the buggy `ok: true` result, so it locks in the wrong behavior. The name "does not throw" frames swallowing the error as the goal. It also never checks the `ok` field or the error content.
**Fix:** Assert the failure contract, for example `resolves.toEqual({ ok: false, error: 'card declined' })`. Also cover a non-`Error` throw and a timeout.

### Observability — Warning

**File:** `src/charge.ts:15`
**Issue:** The exception is silently swallowed. Payment failures are not logged or sent to error tracking, and no customer or invoice context is recorded.
**Fix:** Log a structured error with `customerId` and the amount. Do not log card data. Forward the exception to your error tracker.

### Resilience — Warning

**File:** `src/charge.ts:12-16`
**Issue:** Transient failures (timeouts, 5xx) and permanent ones (declines) are handled the same way. Retry logic cannot tell them apart. There is no idempotency key on `gateway.charge`, so adding retries later could double-charge.
**Fix:** Classify errors, and pass an idempotency key to the gateway before adding any retry.

### Stack-Specific (TypeScript) — Suggestion

**File:** `src/charge.ts:15`
**Issue:** The `catch` has no binding, so nothing is narrowed from `unknown` or used. Once the error is reported, narrow it explicitly.
**Fix:** Use `catch (e: unknown)` and narrow it before use, as in the example above.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 1        | 0       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 0          |     |
| Accessibility         |          |         |            | N/A |
| Observability         | 0        | 1       | 0          |     |
| API Design            |          |         |            | N/A |
| Resilience            | 0        | 1       | 0          |     |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 1          |     |
| **Total**             | **2**    | **2**   | **1**      |     |

**Verdict:** Do not merge. The change reports failed charges as successful.
