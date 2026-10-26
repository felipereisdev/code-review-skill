**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: serve the invoice PDF as a download attachment by adding a `Content-Disposition` header (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The new `Content-Disposition: attachment` header makes browsers save the invoice instead of rendering it inline.
- `Store.Find` binds the id as a `$1` placeholder, so the lookup is not open to SQL injection.
- The route in `cmd/server/main.go:21` is still wrapped in `auth.Require`, so requests with no session are still rejected with 401.

## Findings

### Security — Critical

**Location:** `internal/invoices/handler.go:23-26` (removed old-side lines; the removal of old line 16 `user := auth.UserFrom(r.Context())` and of the `auth` import at old line 7 go with it)
**Issue:** The change deletes the ownership check from `Download`. Any signed-in user can again download any customer's invoice.
**Evidence:** A signed-in user requests `GET /invoices/<another customer's id>` → `Store.Find` returns the invoice whoever owns it (`internal/invoices/store.go:18-28`, which selects by `id` only), and the handler writes `inv.PDF` with 200. The removed `if inv.OwnerID != user.ID { ... 403 }` was the only owner check. Verification checked the route in `cmd/server/main.go:21`, `auth.Require` in `internal/auth/auth.go:16-26` and `Store.Find`. `Require` only checks that a session exists, and its doc comment says "it does not check what the user may access". No other layer enforces ownership. History: git blame at `210a473` shows `8907225` last changed these lines; its message says "fix: only the owner of an invoice can download it (#57)", and its body says any signed-in user could download another customer's invoice by changing the id in the URL. The code shows that this scenario returns.
**Confidence:** High
**Fix:** Restore the check: get the user with `auth.UserFrom(r.Context())` and compare `inv.OwnerID` with `user.ID`. Return 403, or 404 so that invoice ids are not revealed. Alternatively, scope the query to the owner, for example `WHERE id = $1 AND owner_id = $2`. Add a test where user A requests user B's invoice.

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
| Resilience            | 0        | 0       | 0          |     |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **0**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 3/5 — up to 50 changed lines in 1 file; authorization, personal data.
**Relevant tests:** missing — I looked in every tracked file (`git ls-files` lists no `*_test.go` file), so nothing tests `Download`, and nothing would catch the removed ownership check. Execution: not run.
**Look first:** `internal/invoices/handler.go` (the ownership check is removed, so any signed-in user can download any invoice).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 1 of 1 changed files: `internal/invoices/handler.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `internal/invoices/store.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:references/removed-code-history.md`, `skill:references/resilience.md`, `skill:stacks/go.md`.
**Checked with no findings:** Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, API Design, Resilience, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
