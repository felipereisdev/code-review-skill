**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: let the user search endpoint match a user's email as well as their name (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- `app/Http/Controllers/UserSearchController.php:18-21` wraps the `name`/`email` conditions in one closure. The `OR` stays grouped, so any `where` clause added later keeps its precedence.
- The query still binds values through Eloquent. It keeps the `max:100` validation on `q`, the `limit(20)` and the explicit column list, so the new `OR` adds no injection or unbounded-result risk.
- `tests/Feature/UserSearchTest.php:23-31` adds a feature test for the new behavior. It follows the style of the existing name test and uses the same endpoint, `actingAs` and `assertJsonCount`.

## Findings

### Potential Bugs — Suggestion

**Location:** `app/Http/Controllers/UserSearchController.php:19-20`
**Issue:** The user's `q` goes into the `LIKE` patterns unescaped, so `_` and `%` act as wildcards. The change now applies this to `email`, where `_` is common (`john_doe@…`).
**Evidence:** `q=a_b@x.com` → the pattern `%a_b@x.com%` also matches `aXb@x.com`, so unrelated users appear in the 20 results. `q=%` matches every user. Names already behaved this way, but the new email match makes it more visible.
**Confidence:** High
**Fix:** Escape `\`, `%` and `_` in `$validated['q']` before building the pattern. Use `addcslashes($validated['q'], '\\%_')` if the database driver's `LIKE` escape character is a backslash. Otherwise add an explicit `ESCAPE` clause.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 1          |     |
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
| **Total**             | **0**    | **0**   | **1**      |     |

**Verification:** 0 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `tests/Feature/UserSearchTest.php` adds `test_it_finds_users_by_email`, which finds one user by a partial email. It does not cover a non-matching query, the `_`/`%` wildcard case, or several users with the `OR` grouping. Execution: not run.
**Look first:** `app/Http/Controllers/UserSearchController.php` (the new email match and the unescaped `LIKE` pattern), `tests/Feature/UserSearchTest.php` (the only test of the new behavior).
**Ready to merge:** Yes — no Critical or Warning findings.

## Audit

**Files reviewed:** 2 of 2 changed files: `app/Http/Controllers/UserSearchController.php`, `tests/Feature/UserSearchTest.php`.
**Read for context:** `composer.json`, `routes/api.php`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Security, Performance, Tests/Coverage, Architecture, Code & File Size, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
