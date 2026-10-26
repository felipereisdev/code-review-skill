**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: let the user search endpoint match on email as well as name (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The new `orWhere` sits inside a closure, so it is grouped. A later `->where(...)` such as a tenant or active filter will not be bypassed by the `OR`.
- The input is still validated (`required`, `string`, `max:100`). Values go through the query builder as bindings, so there is no SQL injection. The result is still capped with `limit(20)` and selects explicit columns.
- The change comes with a feature test for the new email path. That test would fail without the new `OR` clause.

## Findings

### Privacy/Compliance — Warning (see Needs human verification)

Not counted here. It is under `## Needs human verification` below, because its confidence is Medium.

**Code review passed — no issues found.**

## Needs human verification

### Privacy/Compliance — Warning

**Location:** `app/Http/Controllers/UserSearchController.php:18-21`
**Issue:** Any user authenticated with `auth:sanctum` can now look up other users by email substring. The response still returns the matched user's `email`, so the endpoint now confirms whether an email address is registered.
**Evidence:** Before the change, a caller had to guess a name to see an email. Now an authenticated caller sends `GET /api/users/search?q=jane.doe@target-corp.com`, or a domain such as `q=@target-corp.com`. A hit returns `{id, name, email}`, which confirms the address is registered and ties it to a name. Varying the substring (`q=a@`, `q=b@`, ...) harvests addresses 20 at a time. Verification read `routes/api.php`, which has only `auth:sanctum` on the route. The controller has no policy or `authorize()` call. The repository has no `User` model or policy to narrow the result. The scenario is real for the code as written, but it depends on a product decision I cannot see: whether every authenticated user is meant to see every user's email.
**Confidence:** Medium
**Fix:** Confirm that every authenticated user may search the whole user base by email. If not, scope the query (same team or tenant, or an authorization check) or restrict the email match to exact matches. Return `email` only to callers allowed to see it.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
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
| **Total**             | **0**    | **0**   | **0**      |     |

**Verification:** 1 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `tests/Feature/UserSearchTest.php` adds `test_it_finds_users_by_email`, which searches `ada@example` and expects one result. It does not cover a non-matching query, or a match on another user's email or the case where a name and an email both match. It does not cover access limits between users. Execution: not run.
**Look first:** `app/Http/Controllers/UserSearchController.php` (email lookup open to every authenticated user, with emails in the response), `tests/Feature/UserSearchTest.php` (the new test only searches the signed-in user's own record).
**Ready to merge:** With fixes — a person must check 1 finding under Needs human verification before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `app/Http/Controllers/UserSearchController.php`, `tests/Feature/UserSearchTest.php`.
**Read for context:** `composer.json`, `routes/api.php`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, API Design, Stack-Specific.
**Not verified:** nothing.
