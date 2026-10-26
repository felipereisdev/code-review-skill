**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: move the invoice ownership check from the handler into the SQL query (`FindForOwner`) and serve the PDF as a downloadable attachment (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The ownership rule now lives in the query (`WHERE id = $1 AND owner_id = $2`). The handler cannot forget it, and the data layer never returns another user's invoice. Both values are bound as `$1` and `$2` placeholders, so there is no SQL injection.
- A non-owner now gets the same 404 as a missing invoice, so the endpoint no longer confirms that another customer's invoice id exists.
- The route stays behind `auth.Require` in `cmd/server/main.go:21`, and the handler still takes the user from the request context.
- `Content-Disposition: attachment` makes browsers download the PDF instead of rendering it inline.

## Findings

### Tests/Coverage — Suggestion

**Location:** `internal/invoices/store.go:30-40`
**Issue:** The new ownership-scoped query and the handler change have no test. The repository has no `_test.go` files at all.
**Evidence:** The Go files show no tests for `Download` or `FindForOwner`. A later edit that drops `AND owner_id = $2` from the query, or reverts the handler to the unscoped `Find`, would break nothing in a test run. That is the "any signed-in user can download another customer's invoice" hole that commit `8907225` (#57) fixed.
**Confidence:** High
**Fix:** Add a test for `FindForOwner` and `Download` with two users. The owner gets the PDF, and a non-owner gets 404 with no PDF bytes.

### Architecture — Suggestion

**Location:** `internal/invoices/store.go:30-40`
**Issue:** After this change `Store.Find` has no caller. It is documented as "whoever owns it", so it is an unscoped lookup of any user's invoice sitting beside the scoped one. `FindForOwner` repeats its query and `Scan` almost line for line.
**Evidence:** The handler at `internal/invoices/handler.go:18` was the only caller of `Find`, and a search of the Go files finds no other use. A future handler that calls the unscoped `Find` would bring back the ownership hole that #57 fixed.
**Confidence:** High
**Fix:** Delete `Find`, or make it unexported and use it only for internal or admin paths. If both lookups stay, share the scan code.

## Pre-existing issues (not counted)

- `internal/invoices/handler.go:19-22` — every `FindForOwner` error, including a database outage, is reported as a 404 and is not logged. The `if err != nil` branch is unchanged by this diff.

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
| Privacy/Compliance    |          |         |            | N/A |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **2**      |     |

**Verification:** 2 Critical/Warning candidates checked, 2 refuted.

- The first refuted candidate was header injection through `inv.ID` in `Content-Disposition`. `inv.ID` comes from the database row that matched the owner, and the diff and the code I read show no way for it to carry a quote or line break.
- The second was the removed handler ownership check. The query now enforces ownership (`internal/invoices/store.go:34`), and the route sits behind `auth.Require`, so non-owners still get no PDF. The history of the removed lines gave no other candidate.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; authorization.
**Relevant tests:** missing — I looked for `*_test.go` files in the repository and found none, so nothing covers `Download` or `FindForOwner`. Execution: not run.
**Look first:** `internal/invoices/handler.go` (the ownership check was removed here and the new header is built from `inv.ID`), `internal/invoices/store.go` (the new scoped query, plus `Find`, which is now unused and unscoped).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `internal/invoices/handler.go`, `internal/invoices/store.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/go.md`.
**Checked with no findings:** Security, Performance, Code & File Size, Potential Bugs, API Design, Stack-Specific.
**Not verified:** nothing.
