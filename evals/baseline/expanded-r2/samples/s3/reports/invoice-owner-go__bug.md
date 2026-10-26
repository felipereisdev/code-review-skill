## Scope

**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: add a `Content-Disposition: attachment` header to the invoice PDF download, which also removes the ownership check (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The new `Content-Disposition: attachment` header is a sensible addition: browsers download the PDF instead of rendering it inline. The filename comes from `inv.ID`, a value loaded from the store, not from the raw request path.
- `Store.Find` uses a `$1` placeholder, so the lookup is parameterized.

## Findings

### Security — Critical

**Location:** `internal/invoices/handler.go:23-26` (removed lines, old side; the `user := auth.UserFrom(r.Context())` line at old line 16 and the `auth` import at old line 6 are removed with them)
**Issue:** The change removes the check that only the owner of an invoice can download it (`inv.OwnerID != user.ID` → 403). `Download` now returns any invoice's PDF to any signed-in user. This is broken access control (IDOR) on customer billing documents.
**Evidence:** A signed-in user requests `GET /invoices/<id of another customer's invoice>` → `cmd/server/main.go:21` wraps the handler only in `auth.Require`, which per `internal/auth/auth.go:17` "does not check what the user may access". `Store.Find` (`internal/invoices/store.go:18-28`) loads the invoice "whoever owns it". With the check gone, the handler writes `inv.PDF` for any `id` that exists. Verification checked the route registration, `auth.Require`, `Store.Find` and the diff; nothing else restricts access. History: git blame at `bc3b928` shows `8907225` last changed the removed check; its message says "fix: only the owner of an invoice can download it (#57)" and "Any signed-in user could download another customer's invoice by changing the id in the URL." This is the same scenario, and the removal brings it back.
**Confidence:** High
**Fix:** Restore the ownership check and the `auth` import: get `user := auth.UserFrom(r.Context())` and return 403 when `inv.OwnerID != user.ID`. Keep the new `Content-Disposition` header. Add a regression test for the cross-user case.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 1        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
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
| **Total**             | **1**    | **0**   | **0**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 3/5 — up to 50 changed lines in 1 file; authorization, personal data.
**Relevant tests:** missing — I looked for tests of the invoice handler and found none: `git ls-files` lists no `*_test.go` file in the repository, so no test covers the download path or the ownership rule. Execution: not run.
**Look first:** `internal/invoices/handler.go` (removes the invoice ownership check that fixed #57; any signed-in user can download any invoice).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 1 of 1 changed files: `internal/invoices/handler.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `internal/invoices/store.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:references/removed-code-history.md`, `skill:stacks/go.md`.
**Checked with no findings:** Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
