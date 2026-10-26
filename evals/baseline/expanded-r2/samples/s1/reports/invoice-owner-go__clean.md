**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make the invoice download look up the invoice by id and owner in one query, and serve the PDF as an attachment (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The ownership check moved into the SQL (`WHERE id = $1 AND owner_id = $2`) and uses placeholders. This removes the check-after-fetch step. A request for someone else's invoice now gets the same 404 as a missing one, so invoice ids can't be probed.
- `FindForOwner` documents its contract in its comment, and `Find` is left untouched.
- The handler gets shorter, and the `Content-Disposition` header matches the new doc comment.

## Findings

### Tests/Coverage — Suggestion

**Location:** `internal/invoices/handler.go:18-22`
**Issue:** The change moves the owner-only rule from Go code into a SQL predicate. The repository has no tests for the handler or the store, so nothing guards this rule.
**Evidence:** A later edit drops `AND owner_id = $2` from `FindForOwner`, or points the handler back at `Find` → every authenticated user can download any invoice, and no test fails. I looked for `*_test.go` files and found none.
**Confidence:** High
**Fix:** Add a handler test with two users: the owner gets 200 and the PDF with its `Content-Disposition` header, and a non-owner gets 404. Add a store test for `FindForOwner` with a mismatched owner.

### Architecture — Suggestion

**Location:** `internal/invoices/store.go:30-40`
**Issue:** `FindForOwner` repeats the query and `Scan` of `Find`. After this change `Find` has no caller in the repository: `handler.go` was its only user, and `cmd/server/main.go` doesn't call it. It remains as an exported way to load any user's invoice.
**Evidence:** A future handler calls `Store.Find(ctx, id)` because it is exported and documented as "whoever owns it" → it returns another user's invoice with no ownership check, which is the bug the earlier commit "fix: only the owner of an invoice can download it (#57)" fixed.
**Confidence:** High
**Fix:** Remove `Find` if nothing else needs it. If an unscoped lookup is needed (for example for admin use), rename it to say so, and share the scan code between the two methods.

## Pre-existing issues (not counted)

- `internal/invoices/handler.go:19-22` — any store error, including a database outage or a canceled context, is returned as 404 and is not logged. This code is unchanged, and the new `FindForOwner` call keeps the behavior.

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
| Observability         | 0        | 0       | 0          | N/A |
| API Design            | 0        | 0       | 0          |     |
| Resilience            | 0        | 0       | 0          | N/A |
| DB Migrations         | 0        | 0       | 0          | N/A |
| Concurrency           | 0        | 0       | 0          | N/A |
| i18n                  | 0        | 0       | 0          | N/A |
| Privacy/Compliance    | 0        | 0       | 0          | N/A |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **0**   | **2**      |     |

**Verification:** 2 Critical/Warning candidates checked, 2 refuted.

- **Refuted: removed owner check.** `FindForOwner` still applies `owner_id = $2`. `auth.Require` always sets the user in `cmd/server/main.go:21`. A non-owner gets `sql.ErrNoRows` and then 404.
- **Refuted: header injection.** The `Content-Disposition` header is built from `inv.ID`, which comes from the database row and not from the raw request.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; authorization.
**Relevant tests:** missing — I looked for `*_test.go` files in the repository and found none. Nothing covers the owner and non-owner paths or the new header. Execution: not run.
**Look first:** `internal/invoices/handler.go` (authorization check removed and replaced by the scoped query; the 403 for a non-owner is now a 404), `internal/invoices/store.go` (new `FindForOwner`, `Find` left without callers).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `internal/invoices/handler.go`, `internal/invoices/store.go`.
**Read for context:** `cmd/server/main.go`, `go.mod`, `internal/auth/auth.go`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/removed-code-history.md`, `skill:stacks/go.md`.
**Checked with no findings:** Security, Performance, Code & File Size, Potential Bugs, API Design, Stack-Specific.
**Not verified:** nothing.
