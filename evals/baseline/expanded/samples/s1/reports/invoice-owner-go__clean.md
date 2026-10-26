**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make invoice download check ownership inside the SQL query (`FindForOwner`) and serve the PDF as an attachment (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The ownership check is now part of the query (`WHERE id = $1 AND owner_id = $2`). A separate load-then-compare step can no longer be skipped, and the endpoint no longer reveals which invoice IDs exist. A non-owner gets the same 404 as a missing invoice.
- Both values are passed as `$1`/`$2` placeholders, so there is no SQL injection risk. The `database/sql` precedent in the Go stack file covers this.
- The new method has a doc comment that says what it guarantees, and the unscoped `Find` keeps its "whoever owns it" comment.

## Findings

### Tests/Coverage — Suggestion

**Location:** `internal/invoices/store.go:30-40`
**Issue:** The change moves the access-control rule into the new `FindForOwner` query and changes what `Download` returns to a non-owner (403 becomes 404). No test covers either.
**Evidence:** A later edit to the `WHERE` clause, for example dropping `AND owner_id = $2`, would let any logged-in user download any invoice. Nothing in the repository would fail, because there is no `*_test.go` file anywhere (searched the whole repository).
**Confidence:** High
**Fix:** Add tests for `FindForOwner` and `Download` covering three cases: the owner gets 200 with the `Content-Disposition` header, a different user gets 404, and an unknown id gets 404.

## Pre-existing issues (not counted)

- `internal/invoices/handler.go:19-22` — every store error, including a database outage, is answered with 404 and not logged.

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
| Observability         |          |         |            | N/A |
| API Design            | 0        | 0       | 0          |     |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 3/5 — up to 50 changed lines in 2 files; authorization, public API contracts.
**Relevant tests:** missing — looked for `*_test.go` and any other test files in the repository and found none, so neither `FindForOwner` nor `Download` is tested. Execution: not run.
**Look first:** `internal/invoices/store.go` (new query that now carries the access-control rule, untested), `internal/invoices/handler.go` (status for a non-owner changes from 403 to 404, and a new response header).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `internal/invoices/handler.go`, `internal/invoices/store.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:stacks/go.md`.
**Checked with no findings:** Security, Performance, Architecture, Code & File Size, Potential Bugs, API Design, Stack-Specific.
**Not verified:** nothing.
