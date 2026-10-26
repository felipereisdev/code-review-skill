**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `chargeInvoice` return a value instead of throwing when the payment gateway fails (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change adds a test for the gateway-failure path, so that path is at least exercised.
- `ChargeResult` is a discriminated union with an explicit `ok: false` variant, and `strict` is on in `tsconfig.json`. That is the right shape for reporting a failed charge.

## Findings

### Potential Bugs — Critical

**Location:** `src/charge.ts:15-17`
**Issue:** The new `catch` turns every gateway failure into a successful result, `{ ok: true, chargeId: '' }`. The error is dropped without being logged or rethrown. The `ok: false` variant of `ChargeResult` is now unreachable from this function.
**Evidence:** `gateway.charge(...)` rejects (for example `new Error('card declined')`, a timeout or a network error) → the `catch` returns `{ ok: true, chargeId: '' }` → any caller that checks `result.ok` treats the invoice as paid and stores an empty charge id, although no money was charged. A failed charge is recorded as a successful payment, which corrupts billing state. The reason for the failure is also lost, because nothing is logged or reported. Verification found no other caller in the repository (only `src/charge.ts` and `test/charge.test.ts` exist). The contract that `ok: true` means a charge succeeded comes from the `ChargeResult` type and the success test.
**Confidence:** High
**Fix:** Return the failure that the type already models: `catch (e) { return { ok: false, error: e instanceof Error ? e.message : String(e) }; }`. Log or report the error with the customer and invoice context, but without card data. Alternatively, remove the `try/catch` and let callers handle the rejection.

### Tests/Coverage — Suggestion

**Location:** `test/charge.test.ts:13-16`
**Issue:** The new test only asserts `resolves.toBeDefined()`. It passes for any resolved value, including the wrong `ok: true` result, so it locks in the buggy behavior instead of checking the failure behavior.
**Evidence:** With the current code, `chargeInvoice(failing, 'cus_1', 500)` resolves to `{ ok: true, chargeId: '' }`, and the test passes. After the fix above the test still passes without checking `ok: false`, so it would not catch a regression.
**Confidence:** High
**Fix:** Assert the exact result, for example `resolves.toEqual({ ok: false, error: 'card declined' })`, or `expect(result.ok).toBe(false)`.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 1        | 0       | 0          |     |
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
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test/charge.test.ts` covers the success path (exact `ok: true` and `chargeId`) and a gateway rejection, but the rejection test only asserts that a value is returned, not that the failure is reported. Execution: not run.
**Look first:** `src/charge.ts` (failed charge returned as `ok: true` with an empty `chargeId`), `test/charge.test.ts` (the failure test does not check the result).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/charge.ts`, `test/charge.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/resilience.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Observability, Resilience, Stack-Specific.
**Not verified:** nothing.
