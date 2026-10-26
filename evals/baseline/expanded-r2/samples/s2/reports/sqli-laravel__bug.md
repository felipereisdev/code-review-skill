**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: let the user search endpoint match email as well as name, using a raw SQL query in place of the Eloquent query (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The `q` input is validated (`required`, `string`, `max:100`) before use.
- The route stays behind `auth:sanctum`.
- The query keeps `LIMIT 20` and selects explicit columns instead of `SELECT *`.
- The change comes with a feature test (`test_it_finds_users_by_email`) for the new email matching.

## Findings

### Security — Critical

**Location:** `app/Http/Controllers/UserSearchController.php:18-21`
**Issue:** The search term is interpolated straight into the SQL string passed to `DB::select()`, with no bindings. The previous `where('name', 'like', ...)` call bound the value. This version does not.
**Evidence:** An authenticated user requests `GET /api/users/search?q=x' UNION SELECT id, password, remember_token FROM users-- -`. The payload is a string under 100 characters, so it passes the `required|string|max:100` rule. The interpolated SQL then runs the attacker's `UNION`. The endpoint returns every user's password hash and remember token in the JSON, and the same route allows other injected SQL. A plain `q=O'Brien` also breaks the quoting. It raises a SQL syntax error and the request returns a 500. Verification checked the controller, the validation rule (it only limits type and length) and `routes/api.php` (the route requires login, but any logged-in user can reach it). Nothing escapes or binds `$term`. This is the case the Laravel stack file's "query builder binds values" precedent excludes: raw SQL with input interpolated into the string.
**Confidence:** High
**Fix:** Go back to the query builder, or pass bindings to `DB::select()`. For example:
```php
$like = '%'.$validated['q'].'%';
$users = User::query()
    ->where(fn ($q) => $q->where('name', 'like', $like)->orWhere('email', 'like', $like))
    ->orderBy('name')
    ->limit(20)
    ->get(['id', 'name', 'email']);
```
Alternatively, use `DB::select('... WHERE name LIKE ? OR email LIKE ? ...', [$like, $like])`.

### Tests/Coverage — Suggestion

**Location:** `tests/Feature/UserSearchTest.php:23-31`
**Issue:** The new test only covers a benign email term. No test sends a quote or SQL metacharacters in `q`.
**Evidence:** The new test passes against the vulnerable interpolated query, and so does the existing name test. A regression test like `?q=O'Brien` or a `UNION` payload would have failed with this change (500 or leaked rows). Because of that, the injection above shows up in no test.
**Confidence:** High
**Fix:** Add a test that searches for a term containing `'` and asserts a 200 response and no extra columns or rows. It would guard the parameter binding.

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

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `tests/Feature/UserSearchTest.php` covers search by name and, with the added test, by email. It has no test for special characters or injection payloads. Execution: not run.
**Look first:** `app/Http/Controllers/UserSearchController.php` (Critical SQL injection in the interpolated query), `tests/Feature/UserSearchTest.php` (no test for quotes or injection payloads).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `app/Http/Controllers/UserSearchController.php`, `tests/Feature/UserSearchTest.php`.
**Read for context:** `composer.json`, `routes/api.php`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Performance, Architecture, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
