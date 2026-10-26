## Intent

**Intent:** inferred: extend the user search endpoint so it also matches on email, and add a test for it (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

**Scope:** staged (git diff --cached)

## What Was Done Well

- The change adds `test_it_finds_users_by_email`, so the new email match has a test that follows the existing test's style.
- The `q` validation (`required`, `string`, `max:100`) is kept, and the endpoint stays behind `auth:sanctum` in `routes/api.php:6`.
- The query keeps its explicit column list (`id, name, email`) and its `LIMIT 20`.

## Findings

### Security — Critical

**Location:** `app/Http/Controllers/UserSearchController.php:18-21`
**Issue:** The controller puts the request value `q` straight into a raw SQL string passed to `DB::select()`. It uses no bindings, so this is a SQL injection. The change replaced the Eloquent query, which bound the value, with this raw query.
**Evidence:** An authenticated user calls `GET /api/users/search?q=x' UNION SELECT id, password, email FROM users -- ` (fewer than 100 characters, so it passes `max:100`). The controller interpolates it into `... WHERE name LIKE '%x' UNION SELECT id, password, email FROM users -- %' OR ...`. The query now returns every user's password hash in the `name` field, and the endpoint sends it back as JSON. The same input can read any table. Verification checked the validation rules (`string`, `max:100` do not reject quotes or SQL syntax), the route (`auth:sanctum` only requires any logged-in user), and the call (`DB::select` receives no bindings array). Nothing blocks the input.
**Confidence:** High
**Fix:** Bind the value. For example, use `User::query()->where(fn ($q) => $q->where('name', 'like', "%{$term}%")->orWhere('email', 'like', "%{$term}%"))->orderBy('name')->limit(20)->get(['id', 'name', 'email'])`. If raw SQL is required, use `DB::select('... LIKE ? OR email LIKE ? ...', ["%{$term}%", "%{$term}%"])`. Add a test that sends a quote character in `q` and asserts a normal response with no extra rows.

### Architecture — Suggestion

**Location:** `app/Http/Controllers/UserSearchController.php:18-21`
**Issue:** The change removes the only use of `User` in this controller, but the `use App\Models\User;` import (line 5) stays. It is now dead code.
**Evidence:** The `User::query()` call is gone from `__invoke` → the import is unused and misleads readers. Restoring the Eloquent query, as the Critical finding advises, would use it again.
**Confidence:** High
**Fix:** Use the `User` model again through the Eloquent query, or remove the import.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 1        | 0       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 0       | 0          |     |
| Architecture          | 0        | 0       | 1          |     |
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
**Relevant tests:** changed — `tests/Feature/UserSearchTest.php` covers search by name and the new search by email, each returning one matching user. It does not cover input with quotes or SQL syntax, a search with no match, or the `LIMIT 20` cap. Execution: not run.
**Look first:** `app/Http/Controllers/UserSearchController.php` (Critical SQL injection in the raw query), `tests/Feature/UserSearchTest.php` (no test with special characters in `q`).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `app/Http/Controllers/UserSearchController.php`, `tests/Feature/UserSearchTest.php`.
**Read for context:** `composer.json`, `routes/api.php`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Performance, Tests/Coverage, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
