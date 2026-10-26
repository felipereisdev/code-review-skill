**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `chargeInvoice` stop throwing when the payment gateway fails (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `ChargeResult` is a discriminated union with an `ok: false` variant, so a failed charge already has a place in the type.
- `tsconfig.json` sets `strict: true`.
- The change is small and has a test next to it.

## Findings

### Potential Bugs — Critical

**Location:** `src/charge.ts:15-16`
**Issue:** The new `catch` turns every gateway failure into `{ ok: true, chargeId: '' }`. `ChargeResult` already has `{ ok: false; error: string }` for this case, but the code never returns it.
**Evidence:** `gateway.charge()` rejects (card declined, timeout, gateway outage) → `chargeInvoice` resolves `{ ok: true, chargeId: '' }`. Any consumer that branches on `ok` treats the invoice as paid and stores an empty charge id, so the data says "paid" when no money was taken. Verification checked the repository: `chargeInvoice` is only declared in `src/charge.ts` and nothing in the repo calls it, so the consumers are outside it. The success flag and the empty `chargeId` are visible in the changed lines, and `ChargeResult` is the contract those consumers rely on. Nothing upstream, in the types or in the tests prevents the scenario. The only new test passes with this behavior.
**Confidence:** High
**Fix:** Return the failure variant, for example `catch (err) { return { ok: false, error: err instanceof Error ? err.message : 'charge failed' }; }`. Never return `ok: true` with a placeholder `chargeId`. Rethrow errors you cannot map to a declined charge.

### Tests/Coverage — Suggestion

**Location:** `test/charge.test.ts:13-16`
**Issue:** The new test only asserts `resolves.toBeDefined()`. It checks that the call does not throw and says nothing about the result. It passes against the `ok: true` bug above and would also pass with a correct `ok: false` result, so it can't catch the regression.
**Evidence:** The failing gateway throws `Error('card declined')` → `chargeInvoice` returns `{ ok: true, chargeId: '' }` → `toBeDefined()` passes, so the suite stays green.
**Confidence:** High
**Fix:** Assert the contract, for example `resolves.toEqual({ ok: false, error: 'card declined' })`. Add a case for a non-`Error` rejection.

### Observability — Suggestion

**Location:** `src/charge.ts:15`
**Issue:** The `catch` binds no error and does not log or report it, so the cause of a failed charge is lost.
**Evidence:** The gateway rejects with a decline or an outage → the error is discarded → neither logs nor error tracking show why charges fail.
**Confidence:** High
**Fix:** Keep the error and put its message in the `ok: false` result. Log or report it through the project's logging or error-tracking tool, without card or customer data.

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
| Observability         | 0        | 0       | 1          |     |
| API Design            |          |         |            | N/A |
| Resilience            | 0        | 0       | 0          |     |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **2**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test/charge.test.ts` covers the success path (`ch_123`) and a rejecting gateway, but the failure test only asserts that the result is defined, not its content. Execution: not run.
**Look first:** `src/charge.ts` (the catch reports a failed charge as `ok: true`), `test/charge.test.ts` (the failure test asserts nothing about the result).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/charge.ts`, `test/charge.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/resilience.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Resilience, Stack-Specific.
**Not verified:** nothing.
