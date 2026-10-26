**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: serve the invoice PDF as a download attachment by adding a `Content-Disposition` header (diff). The same diff also deletes the ownership check from `Download`.
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- Adding `Content-Disposition: attachment` is a sensible change. It makes browsers download the invoice instead of rendering it inline.
- The doc comment on `Download` was updated to match the new behavior.
- `Store.Find` still uses a `$1` placeholder, so the lookup stays parameterized.

## Findings

### Security — Critical

**Location:** `internal/invoices/handler.go:23-26` (removed lines of the old file; the `user := auth.UserFrom(...)` line and the `auth` import are removed with them)
**Issue:** The change deletes the ownership check from `Download`: `if inv.OwnerID != user.ID { ... 403 }`. Any signed-in user can now download any customer's invoice by changing the id in the URL.
**Evidence:** A signed-in user requests `GET /invoices/<another customer's invoice id>` → `Store.Find` loads the invoice "whoever owns it" (`internal/invoices/store.go:18-23`) and the handler writes `inv.PDF` with no owner comparison, so one customer's invoice (personal and financial data) is disclosed to another. Verification checked the only route, `cmd/server/main.go:21`, and `auth.Require` at `internal/auth/auth.go:16-26`. `Require` only checks that a session exists ("it does not check what the user may access"), and nothing else in the repository compares `OwnerID` to the user. History: git blame at `939cf51` shows `8907225` last changed the removed `if inv.OwnerID != user.ID` line, and git log -S lists it as changing text matching `inv.OwnerID != user.ID`. Its message says "fix: only the owner of an invoice can download it (#57)" and "Any signed-in user could download another customer's invoice by changing the id in the URL." The staged diff therefore brings back the problem that #57 fixed.
**Confidence:** High
**Fix:** Restore the check in `Download`: get `user := auth.UserFrom(r.Context())` and return 403 when `inv.OwnerID != user.ID`. Keep the new `Content-Disposition` header. If you want to hide that an invoice exists, return 404 instead of 403.

### Tests/Coverage — Suggestion

**Location:** `internal/invoices/handler.go:12-22`
**Issue:** The repository has no tests for `Download`, and this change shows the cost. The ownership rule from #57 has no regression test, so removing it breaks nothing in a test run.
**Evidence:** `git ls-files` lists no `*_test.go` file → deleting the owner check in this diff fails no test.
**Confidence:** High
**Fix:** Add a handler test, with a fake store or `sqlmock`, covering these cases: the owner gets 200 with the PDF and the attachment header, a non-owner gets 403, and an unknown id gets 404.

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

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 3/5 — up to 50 changed lines in 1 file; authorization, personal data.
**Relevant tests:** missing — I looked for tests of `internal/invoices/handler.go` in the whole repository (`git ls-files`) and found none, so nothing covers the download or the ownership rule. Execution: not run.
**Look first:** `internal/invoices/handler.go` (the ownership check is removed, so any signed-in user can download any invoice).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 1 of 1 changed files: `internal/invoices/handler.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `internal/invoices/store.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:references/removed-code-history.md`, `skill:stacks/go.md`.
**Checked with no findings:** Performance, Architecture, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
