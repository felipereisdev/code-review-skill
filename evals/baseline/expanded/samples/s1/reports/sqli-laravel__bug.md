**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: make the user search endpoint match on email as well as name, and rewrite its query as a raw SQL string (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The existing `q` validation (`required`, `string`, `max:100`) is kept.
- The route stays behind `auth:sanctum` (`routes/api.php:6`).
- The change adds a feature test for the new email search.

## Findings

### Security — Critical

**Location:** `app/Http/Controllers/UserSearchController.php:18-21`
**Issue:** The change replaces the Eloquent query, which bound the search term, with `DB::select()` on a string that interpolates the user's `q` value (`'%{$term}%'`). The term is never bound or escaped, so this is SQL injection.
**Evidence:** An authenticated user calls `GET /api/users/search?q=x%' UNION SELECT id, <any column>, <any column> FROM <any table> -- ` (well under the 100-character limit).
- The query becomes `... name LIKE '%x%' UNION SELECT ... -- %' OR email LIKE ...`, and the response JSON returns the rows of the injected query, so other columns and other tables are readable.
- Even a benign `q=O'Brien` breaks the SQL string and the request fails with a database error (HTTP 500).
- Verification checked the validation rules (they only require a string of at most 100 characters), the route (`auth:sanctum` limits who can call it, not what they send), and the project's only caller path. Nothing strips quotes or binds the value.
- The Laravel precedent that query-builder values are bound does not apply: the exception for raw SQL with interpolated input is exactly this case.
**Confidence:** High
**Fix:** Go back to bound parameters. With the query builder:
```php
$like = '%'.addcslashes($validated['q'], '%_\\').'%';
$users = User::query()
    ->where(fn ($q) => $q->where('name', 'like', $like)->orWhere('email', 'like', $like))
    ->orderBy('name')
    ->limit(20)
    ->get(['id', 'name', 'email']);
```
If raw SQL is kept, use `DB::select('... LIKE ? OR email LIKE ? ...', [$like, $like])`. Add a test with a quote character and a `UNION` payload in `q`.

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

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `tests/Feature/UserSearchTest.php` adds `test_it_finds_users_by_email`, which covers the happy path of an email match. No test covers quotes or injection payloads in `q`. Execution: not run.
**Look first:** `app/Http/Controllers/UserSearchController.php` (Critical SQL injection from the interpolated raw query).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `app/Http/Controllers/UserSearchController.php`, `tests/Feature/UserSearchTest.php`.
**Read for context:** `composer.json`, `routes/api.php`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Performance, Tests/Coverage, Architecture, Code & File Size, Potential Bugs, API Design, Privacy/Compliance, Stack-Specific.
**Not verified:** nothing.
