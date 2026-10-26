**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make the invoice download check ownership inside the database query (`FindForOwner`) and serve the PDF as an attachment (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The ownership check moved into the SQL (`WHERE id = $1 AND owner_id = $2`) and uses placeholders. The check and the load are now one step, so a handler can no longer load an invoice and forget the owner test.
- A non-owner now gets the same 404 as a missing invoice. Before, the 403 confirmed that an invoice id exists.
- The route is still mounted behind `auth.Require` in `cmd/server/main.go:21`, so `user` is always set when `Download` runs.
- Adding `Content-Disposition: attachment` makes browsers download the file instead of rendering it.

## Findings

### Tests/Coverage — Suggestion

**Location:** `internal/invoices/store.go:30-40`
**Issue:** The change moves an access-control rule from the handler into a new query, and the repository has no test for it.
**Evidence:** A later edit drops `AND owner_id = $2` from `FindForOwner` → any logged-in user can download any invoice, and no test fails. The repository has no `_test.go` files.
**Confidence:** High
**Fix:** Add a store or handler test with two users. The owner gets the PDF with 200, a non-owner gets 404, and an unknown id gets 404.

### Architecture — Suggestion

**Location:** `internal/invoices/handler.go:18`
**Issue:** Moving to `FindForOwner` leaves `Store.Find` (`store.go:18-28`) with no callers. It is an exported, unscoped lookup that ignores ownership, and its query duplicates the new one.
**Evidence:** A grep for `.Find(` finds no remaining call. A future handler that picks `Find` because it is the obvious name → serves another user's invoice, which is the bug fixed in #57.
**Confidence:** High
**Fix:** Delete `Find`, or make it unexported and use it only for internal jobs.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 1          |     |
| Architecture          | 0        | 0       | 1          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 0          |     |
| Accessibility         | 0        | 0       | 0          | N/A |
| Observability         | 0        | 0       | 0          |     |
| API Design            | 0        | 0       | 0          |     |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **2**      |     |

**Verification:** 1 Critical/Warning candidates checked, 1 refuted. The refuted candidate was header injection through `inv.ID` in the `Content-Disposition` filename. `inv.ID` comes from a row that matched the request id exactly, and Go's `net/http` replaces line breaks in header values.

**Review effort:** 3/5 — up to 50 changed lines in 2 files; authorization, personal data.
**Relevant tests:** missing — I looked for `*_test.go` files in the repository and found none, so nothing covers `FindForOwner` or `Download`. Execution: not run.
**Look first:** `internal/invoices/store.go` (new ownership query with no test), `internal/invoices/handler.go` (ownership check removed from the handler and the response contract changed from 403 to 404).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `internal/invoices/handler.go`, `internal/invoices/store.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/observability.md`, `skill:references/privacy.md`, `skill:references/removed-code-history.md`, `skill:stacks/go.md`.
**Checked with no findings:** Security, Performance, Code & File Size, Potential Bugs, Observability, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
