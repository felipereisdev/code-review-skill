**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: serve the invoice PDF as a download attachment by adding a `Content-Disposition` header (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The `Content-Disposition: attachment` header gives browsers a clear filename for the download, and the name comes from the stored invoice ID, not from the raw URL.
- The `Download` doc comment was updated to match the new behavior.

## Findings

### Security — Critical

**Location:** `internal/invoices/handler.go:21-24` (removed old-side lines: the `auth.UserFrom` lookup at old line 16 and the ownership check at old lines 23-26)
**Issue:** The change removes the ownership check from `GET /invoices/{id}`. Any signed-in user can now download any other customer's invoice, which is broken access control on personal and billing data.
**Evidence:** User A is signed in, so `auth.Require` accepts the request. A sends `GET /invoices/<id of user B's invoice>` → `Handler.Download` calls `Store.Find`, which runs `SELECT ... WHERE id = $1` with no owner filter, and it returns B's PDF with status 200. Verification checked every path that could still enforce ownership:
- `internal/auth/auth.go:16-26` (`Require`) only checks that a session user exists, and its own comment says it "does not check what the user may access".
- `internal/invoices/store.go:18-23` documents `Find` as loading an invoice "whoever owns it" and filters only on `id`.
- `cmd/server/main.go:21` mounts the handler behind `auth.Require` only.

None of these three replaces the removed check, and the diff adds no other one. History: git blame at `25e638c` shows `8907225` last changed the removed lines. Its message says "fix: only the owner of an invoice can download it (#57)" and that any signed-in user could download another customer's invoice by changing the id in the URL. The code above shows that this is the scenario the change brings back.
**Confidence:** High
**Fix:** Restore the check: read `auth.UserFrom(r.Context())` and compare `inv.OwnerID` with `user.ID`, returning 403 (or 404, to avoid revealing which IDs exist) when they differ. A sturdier option is to make the owner part of the query, for example `Find(ctx, id, ownerID)` with `WHERE id = $1 AND owner_id = $2`, so no caller can skip the check. Add a regression test for the cross-user case.

## Pre-existing issues (not counted)

- `internal/invoices/handler.go:20` — `w.Write(inv.PDF)` ignores its error, so a failed or partial write goes unnoticed.

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
**Relevant tests:** missing — I looked for `*_test.go` files in the repository (`git ls-files` lists 5 files, none a test) and found none, so neither the download handler nor its ownership check has a test. Execution: not run.
**Look first:** `internal/invoices/handler.go` (the ownership check is removed from the invoice download, a Critical access-control regression).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 1 of 1 changed files: `internal/invoices/handler.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `internal/invoices/store.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:references/removed-code-history.md`, `skill:stacks/go.md`.
**Checked with no findings:** Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
