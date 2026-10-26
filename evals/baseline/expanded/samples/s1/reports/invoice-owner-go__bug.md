## Scope

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make `GET /invoices/{id}` return the PDF as a download attachment (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The new `Content-Disposition: attachment` header makes the PDF download as a file instead of rendering inline.
- `Store.Find` keeps the `$1` placeholder for the id, so the lookup stays parameterized.

## Findings

### Security — Critical

**Location:** `internal/invoices/handler.go:23-26` (removed lines; the `auth` import and `user := auth.UserFrom(...)` at old lines 7 and 16 are removed with them)
**Issue:** The change removes the ownership check (`inv.OwnerID != user.ID` → 403) from `Download`. Any signed-in user can download any customer's invoice.
**Evidence:** A signed-in user requests `GET /invoices/<another customer's id>` → `auth.Require` (`internal/auth/auth.go:16-26`) only checks that a session cookie maps to a user, and its comment says it does not check what the user may access. `Store.Find` (`internal/invoices/store.go:18-28`) loads the invoice by id "whoever owns it". With the check gone, the handler writes `inv.PDF` to that user, so another customer's invoice is disclosed. Verification checked the route in `cmd/server/main.go:21`, `auth.Require`, `Store.Find` and the rest of the new handler, and none of them checks ownership. History: git blame at `d14f370` shows `8907225` last changed the removed `if inv.OwnerID != user.ID` line; its message says "fix: only the owner of an invoice can download it (#57)" and that any signed-in user could download another customer's invoice by changing the id in the URL.
**Confidence:** High
**Fix:** Restore the ownership check: read `user := auth.UserFrom(r.Context())` again and return 403 (or 404, to avoid revealing which ids exist) when `inv.OwnerID != user.ID`. Keep the new `Content-Disposition` header.

### Tests/Coverage — Suggestion

**Location:** `internal/invoices/handler.go:12-22`
**Issue:** The repository has no test for `Download`, so nothing catches the removal of the ownership check.
**Evidence:** The change removes the 403 path and no test fails, because the repository has no `_test.go` file.
**Confidence:** High
**Fix:** Add a handler test where user B requests user A's invoice and expects 403/404. Add a second test where the owner receives the PDF with the attachment header.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 1        | 0       | 0          |     |
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
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **1**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 3/5 — up to 50 changed lines in 1 file; authorization, personal data.
**Relevant tests:** missing — I looked for test files in the repository (`git ls-files` lists no `_test.go` file) and found none, so nothing covers `Download` or the removed ownership check. Execution: not run.
**Look first:** `internal/invoices/handler.go` (removes the invoice ownership check, so any signed-in user can download any invoice).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 1 of 1 changed files: `internal/invoices/handler.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `internal/invoices/store.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:references/removed-code-history.md`, `skill:stacks/go.md`.
**Checked with no findings:** Performance, Architecture, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
