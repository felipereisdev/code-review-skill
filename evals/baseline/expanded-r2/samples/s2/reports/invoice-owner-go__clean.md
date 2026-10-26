**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make the owner check on invoice download part of the database query (`FindForOwner`), and serve the PDF as a named attachment (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The ownership check moved into the query (`WHERE id = $1 AND owner_id = $2`), so the handler can no longer fetch another user's invoice and forget to compare owners. The earlier fix in #57 is still enforced.
- Both queries use `$n` placeholders, so there is no SQL injection risk (Go precedent: `database/sql` placeholders).
- Returning 404 for an invoice the user does not own no longer confirms that the invoice id exists.
- `Content-Disposition` gives the download a sensible file name.

## Findings

### Tests/Coverage — Suggestion

**Location:** `internal/invoices/handler.go:18-25`, `internal/invoices/store.go:30-40`
**Issue:** The authorization change and the new `FindForOwner` query have no tests. The repository contains no `_test.go` file.
**Evidence:** A later edit to `FindForOwner`, such as dropping `AND owner_id = $2`, would let any logged-in user download any invoice, and no test would fail. This is a Suggestion because the code is correct today.
**Confidence:** High
**Fix:** Add a handler or store test with two users. The owner gets 200 with the PDF and the `Content-Disposition` header. The other user gets 404 and no PDF bytes.

### Architecture — Suggestion

**Location:** `internal/invoices/handler.go:18`
**Issue:** Removing the `Find` call leaves `Store.Find` (`store.go:18-28`) with no callers. It is an exported lookup by id alone, "whoever owns it", next to the new scoped `FindForOwner`, and the two queries are near-duplicates.
**Evidence:** A grep for `.Find(` across the repository finds no remaining caller. A future handler that picks `Find` because it is the shorter name would skip the owner check and bring back the problem fixed in #57.
**Confidence:** High
**Fix:** Delete `Find`. If an unscoped lookup is needed later, name it so the missing owner check is obvious, or add it when needed.

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

**Verification:** 2 Critical/Warning candidates checked, 2 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; authorization.
**Relevant tests:** missing — I looked for tests of the changed code with `git ls-files` and a grep for `_test` in `*.go` files. The repository has no test files, so nothing covers the owner check or the new header. Execution: not run.
**Look first:** `internal/invoices/store.go` (the new `FindForOwner` query now carries the authorization), `internal/invoices/handler.go` (status changes from 403 to 404, new `Content-Disposition` header).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `internal/invoices/handler.go`, `internal/invoices/store.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:references/removed-code-history.md`, `skill:stacks/go.md`.
**Checked with no findings:** Security, Performance, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
