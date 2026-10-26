**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: serve the invoice PDF as a download attachment by adding a `Content-Disposition` header, and drop the per-user ownership check from `Download` (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The new `Content-Disposition: attachment` header gives clients a sensible download filename, and the invoice ID from the database goes into it.
- `Store.Find` still uses a `$1` placeholder, so the lookup stays parameterized.

## Findings

### Security — Critical

**Location:** `internal/invoices/handler.go:23-26` (removed old-side lines; the matching `user := auth.UserFrom(...)` and `auth` import are removed at old lines 7 and 16)
**Issue:** The change removes the ownership check (`inv.OwnerID != user.ID` → 403) from `Download`. After it, any signed-in user can download any invoice.
**Evidence:** A signed-in user requests `GET /invoices/<another customer's id>` → `Store.Find` loads the invoice by id alone, with no owner filter (`internal/invoices/store.go:18-23`). The handler then writes `inv.PDF` to the response, so the other customer's invoice is disclosed. Verification checked the only route (`cmd/server/main.go:21`) and `auth.Require` (`internal/auth/auth.go:16-26`). `Require` only checks that a session exists, and its comment says it "does not check what the user may access". No other check remains in the diff or in the callers. History: git blame at `40da7cf` shows `8907225` last changed the removed line `if inv.OwnerID != user.ID {`, and `git log -S` lists the same commit; its message says "fix: only the owner of an invoice can download it (#57)" and "Any signed-in user could download another customer's invoice by changing the id in the URL." The code confirms that this scenario is possible again.
**Confidence:** High
**Fix:** Restore the check: read `user := auth.UserFrom(r.Context())` and return 403 when `inv.OwnerID != user.ID`. Alternatively, filter by owner in the query, for example `WHERE id = $1 AND owner_id = $2`, and return 404 so invoice IDs are not revealed. Add a regression test for #57 so removing the check fails a test.

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

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 3/5 — up to 50 changed lines in 1 file; authorization, personal data.
**Relevant tests:** missing — the repository has no `*_test.go` files, so nothing covers `Download` or the ownership rule it enforced. Execution: not run.
**Look first:** `internal/invoices/handler.go` (the ownership check is removed, so any signed-in user can download any invoice).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 1 of 1 changed files: `internal/invoices/handler.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `internal/invoices/store.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:references/removed-code-history.md`, `skill:stacks/go.md`.
**Checked with no findings:** Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
