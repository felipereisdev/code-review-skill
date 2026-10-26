**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `chargeInvoice` return a result instead of throwing when the payment gateway fails (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `ChargeResult` is a discriminated union with an explicit `{ ok: false; error: string }` variant. A gateway failure can be reported without throwing.
- The change adds a test for the gateway-failure path, and `PaymentGateway` is an injectable interface, so the test needs no real gateway.

## Findings

### Potential Bugs — Critical

**Location:** `src/charge.ts:12-17`
**Issue:** The new `catch` block swallows every gateway error and returns `{ ok: true, chargeId: '' }`. A failed charge is reported as a successful one, with an empty charge id. The `{ ok: false, error }` variant of `ChargeResult` is never returned. The error is also not logged or re-thrown, so nothing records why the charge failed.
**Evidence:** `gateway.charge('cus_1', 500)` rejects with a declined card, a timeout or a network error → `chargeInvoice` resolves `{ ok: true, chargeId: '' }`. Any caller that branches on `ok` treats the invoice as paid and records a payment that never happened. The customer is not charged, the billing state is wrong, and there is no charge id to reconcile against. Verification checked the repository: `src/charge.ts` is the only source file, so no caller or upstream guard handles the empty `chargeId`. The `ok: true` branch of the return type promises a real charge id, and `''` breaks that. The new test only runs this path and passes.
**Confidence:** High
**Fix:** Return the failure through the existing contract, for example `catch (e) { return { ok: false, error: e instanceof Error ? e.message : 'charge failed' }; }`. Log the original error with the customer id, and not the card data. Do not return `ok: true` without a real `charge.id`.

### Tests/Coverage — Suggestion

**Location:** `test/charge.test.ts:13-16`
**Issue:** The new test asserts only `resolves.toBeDefined()`. It passes for any resolved value, so it checks neither the `ok` flag nor the `chargeId` or `error` content. It passes with the current behavior, where a declined card yields `ok: true`.
**Evidence:** `failing.charge` throws `Error('card declined')` → `chargeInvoice` resolves `{ ok: true, chargeId: '' }` → `toBeDefined()` passes. The test would also pass if the function returned `{ ok: false, error: 'card declined' }` or `{ ok: true }`, so it cannot catch the bug above.
**Confidence:** High
**Fix:** Assert the failure shape, for example `resolves.toEqual({ ok: false, error: 'card declined' })`, once the function returns the failure.

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

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test/charge.test.ts` covers the success path (`ch_123`) and a gateway failure, but the failure test asserts only `toBeDefined()`, so it does not check the returned `ok` flag, `chargeId` or error. Execution: not run.
**Look first:** `src/charge.ts` (the catch block reports a failed payment as `ok: true`), `test/charge.test.ts` (the failure test passes with the bug).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/charge.ts`, `test/charge.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/resilience.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Resilience, Stack-Specific.
**Not verified:** nothing.
