**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: move the invoice ownership check into the SQL query (`FindForOwner`) and serve the PDF as a download attachment (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The ownership check now sits in the query (`WHERE id = $1 AND owner_id = $2`). A non-owner never loads the PDF bytes, and the check and the load can't drift apart.
- Both values go through `$1`/`$2` placeholders, so the new query is parameterized.
- A non-owner now gets 404 instead of 403, so the endpoint no longer reveals which invoice ids exist.
- `Content-Disposition: attachment` makes browsers download the PDF instead of rendering it inline.

## Findings

### Architecture — Suggestion

**Location:** `internal/invoices/handler.go:18`
**Issue:** This change removes the only caller of `Store.Find`. `Find` is exported, returns any invoice regardless of owner, and now duplicates `FindForOwner`'s query.
**Evidence:** `Find` has no callers left (searched all `*.go` files). A later handler that calls `Find` reintroduces the missing-owner-check bug fixed in #57. A future edit to one of the two near-identical queries can also leave the other behind.
**Confidence:** High
**Fix:** Delete `Find`, or make it unexported and keep it only if a non-user-facing caller needs it.

### Tests/Coverage — Suggestion

**Location:** `internal/invoices/store.go:30-40`
**Issue:** The new authorization query and the changed handler have no tests. The repository has no `_test.go` files.
**Evidence:** A user requests `/invoices/{id}` for an invoice owned by someone else → the only protection is the `owner_id = $2` clause. A regression there (for example, a dropped argument) would hand out other users' invoices with no test failing.
**Confidence:** High
**Fix:** Add a handler or store test with two users and one invoice. Assert that the owner gets 200 with the PDF and `Content-Disposition`, and that a non-owner gets 404.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 1          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         |          |         |            | N/A |
| Observability         |          |         |            | N/A |
| API Design            | 0        | 0       | 0          |     |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **2**      |     |

**Verification:** 1 Critical/Warning candidates checked, 1 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; authorization.
**Relevant tests:** missing — I looked for tests of `Handler.Download` and `Store.FindForOwner` and found no `_test.go` file in the repository, so nothing covers the owner and non-owner paths. Execution: not run.
**Look first:** `internal/invoices/handler.go` (ownership check moved into the query, 403 changed to 404, new `Content-Disposition` header), `internal/invoices/store.go` (new authorization query without tests).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `internal/invoices/handler.go`, `internal/invoices/store.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/go.md`.
**Checked with no findings:** Security, Performance, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
