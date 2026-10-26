I read the diff and the repository files and ran the checklist in a single pass; subagents weren't available. This is the report.

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `chargeInvoice` return `{ ok: false, error }` when the gateway call throws, instead of letting the exception propagate (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The catch narrows `error` with `instanceof Error` and falls back to `String(error)`. This fits the project's `strict` TypeScript setup and the `catch` guidance in the TypeScript checklist.
- The change uses the existing `ChargeResult` discriminated union, so the failure branch is typed.
- The change adds a test for the new failure path beside the success test, and it asserts the whole returned object.

## Findings

**Code review passed — no issues found.** is not applicable: the only Warning candidate sits under Needs human verification, so the headline is:

Review incomplete or pending — no confirmed findings in the code inspected.

## Needs human verification

### Resilience — Warning

**Location:** `src/charge.ts:12-18`
**Issue:** Every error from `gateway.charge` is now turned into `{ ok: false, error: message }`. A declined card, a network timeout and an unknown outcome all produce the same result shape. Nothing is logged or reported, and the raw gateway message is returned.
**Evidence:** Trigger: `gateway.charge` times out or the connection drops after the gateway has already created the charge → the `catch` returns `{ ok: false, error: 'timeout' }`. A caller that reads `ok: false` as "not charged" and retries or re-queues the invoice could charge the customer twice, because neither `chargeInvoice` nor `gateway.charge` carries an idempotency key. During a gateway outage, every charge returns `ok: false` and nothing is logged or reported in this function. Verification searched the repository: `src` and `test` hold only `charge.ts` and `charge.test.ts`, so no caller of `chargeInvoice` is in this repository. A person must check how the callers outside it handle `ok: false`, whether they retry, and whether they log or report failures.
**Confidence:** Medium
**Fix:** Return the failure categories separately, for example `declined` versus `unknown`, and rethrow or flag errors where the outcome is unknown. Pass an idempotency key to `gateway.charge`, and log or report the original error before returning.

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

The Suggestion counted under Tests/Coverage is:

- `test/charge.test.ts:13-16` — Suggestion: the new test only throws an `Error`, so the `String(error)` branch at `src/charge.ts:16` is untested. For example, a gateway that rejects with a plain string is not covered. Add a case such as `charge: async () => { throw 'boom'; }` and expect `{ ok: false, error: 'boom' }`.

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; payments.
**Relevant tests:** changed — `test/charge.test.ts` covers the success path and a gateway rejection with an `Error` ('card declined'); it leaves out non-`Error` rejections and the unknown-outcome case from the finding above. Execution: not run.
**Look first:** `src/charge.ts` (payment failures collapsed into one `ok: false` result, with no logging; Warning under Needs human verification), `test/charge.test.ts` (the non-`Error` branch is untested).
**Ready to merge:** With fixes — a person must check 1 finding under Needs human verification before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `src/charge.ts`, `test/charge.test.ts`.
**Read for context:** `package.json`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/resilience.md`, `skill:stacks/node.md`, `skill:stacks/typescript.md`, `tsconfig.json`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, Observability, Stack-Specific.
**Not verified:**
- callers of `chargeInvoice` — context not read, not material: the repository has no caller of `chargeInvoice` (`src` and `test` hold only `charge.ts` and its test). Every changed behavior was judged from the code in the repository, and how outside callers treat `ok: false` is the point of the Needs human verification finding.
