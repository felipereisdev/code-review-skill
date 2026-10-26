**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: extend the user search endpoint so it also matches on email, and rewrite the query as raw SQL (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The change adds a feature test for the new email search (`tests/Feature/UserSearchTest.php:23-31`), alongside the existing name test.
- The request validation (`required`, `string`, `max:100`) and the `auth:sanctum` route middleware are unchanged, so the endpoint stays authenticated and its input stays bounded.
- The `LIMIT 20` cap and the explicit column list (`id, name, email`) are kept, so the response still never carries `password` or other columns.

## Findings

### Security — Critical

**Location:** `app/Http/Controllers/UserSearchController.php:18-21`
**Issue:** The search term is interpolated straight into the SQL string passed to `DB::select()`, so the query is open to SQL injection. The previous Eloquent `where('name', 'like', ...)` sent the value as a PDO binding. The raw query replaces it.
**Evidence:** An authenticated user (any Sanctum token) calls `GET /api/users/search?q=x%' UNION SELECT id, password, email FROM users -- ` (about 50 characters, under the `max:100` rule). The resulting SQL is `... name LIKE '%x%' UNION SELECT id, password, email FROM users -- %' OR ...`, and the JSON response returns every user's password hash in the `name` field. The same input can read any other table. Verification checked the route (`routes/api.php:6`, authentication only, no authorization or throttling) and the validation rule (`q` only has to be a string of at most 100 characters). Neither stops quotes or SQL keywords, and no other code binds the term. The Laravel precedent that "the query builder binds values" does not apply, because this is a raw string with interpolated input.
**Confidence:** High
**Fix:** Go back to bound parameters. Either use Eloquent, `User::query()->where(fn ($q) => $q->where('name', 'like', "%{$term}%")->orWhere('email', 'like', "%{$term}%"))->orderBy('name')->limit(20)->get(['id', 'name', 'email'])`, or keep `DB::select()` with placeholders (`... LIKE ? OR email LIKE ?`) and pass `['%'.$term.'%', '%'.$term.'%']`. Escape `%` and `_` in the term if literal matching is wanted.

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/UserSearchTest.php:23-31`
**Issue:** The new test covers only the happy path of the email match. Nothing covers input with SQL metacharacters (`'`, `%`) or a search with no match, so the injection above passes the suite unnoticed.
**Evidence:** `?q=' OR '1'='1` returns all users, or a database error, and no test fails, because the only assertions are one-row matches for `Ada` and `ada@example`.
**Confidence:** High
**Fix:** Add a regression test that creates two users, searches with a quote-containing term, and asserts that the response is `assertOk()` and returns only the matching rows. Add a no-match case that asserts `assertJsonCount(0)`.

### Architecture — Suggestion

**Location:** `app/Http/Controllers/UserSearchController.php:19-21`
**Issue:** The change removes the only use of `App\Models\User`, but the `use App\Models\User;` import (line 5) stays and is now dead. The controller also now bypasses the Eloquent model, against the Laravel checklist (use the model and avoid raw queries unless necessary).
**Evidence:** The `User` class is no longer referenced anywhere in the file, and a reader sees an unused import next to a hand-written SQL string.
**Confidence:** High
**Fix:** Restoring the Eloquent query (see the Critical finding) uses the import again. Otherwise remove the import.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 1        | 0       | 0          |     |
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
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns | 0        | 0       | 0          | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **1**    | **0**   | **2**      |     |

**Verification:** 1 Critical/Warning candidate checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `test_it_finds_users_by_name` (existing) and the new `test_it_finds_users_by_email` cover the happy-path name and email matches; they leave out special characters, no-match results and validation failures. Execution: not run.
**Look first:** `app/Http/Controllers/UserSearchController.php` (Critical SQL injection in the raw query), `tests/Feature/UserSearchTest.php` (no test that would catch it).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `app/Http/Controllers/UserSearchController.php`, `tests/Feature/UserSearchTest.php`.
**Read for context:** `composer.json`, `routes/api.php`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Performance, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
