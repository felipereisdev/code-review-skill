**Scope:** staged (git diff --cached)

## Intent

**Intent:** inferred: extend the user search endpoint so it also matches on email, and rewrite the query as raw SQL (diff).
**Requirements:** none stated.
**Scope creep:** not judged: no source states a requirement.
**Sources not read:** none.

## What Was Done Well

- The request is still validated (`required`, `string`, `max:100`), and the route stays behind `auth:sanctum`.
- The new feature test, `test_it_finds_users_by_email`, matches the style of the existing name test.
- The result set is still capped at 20 rows and returns only `id`, `name` and `email`.

## Findings

### Security — Critical

**Location:** `app/Http/Controllers/UserSearchController.php:18-21`
**Issue:** The search term is interpolated straight into a raw SQL string passed to `DB::select()`. The old code used the query builder, which binds values. The `q` rule only checks that the value is a string of at most 100 characters, so quotes and SQL syntax pass through.
**Evidence:** An authenticated user calls `GET /api/users/search?q=x%' UNION SELECT id, password, remember_token FROM users -- -`. The payload is under 100 characters and the validation accepts it. The query becomes `... name LIKE '%x%' UNION SELECT id, password, remember_token FROM users -- -%' OR email LIKE ...`. The response then returns password hashes and remember tokens for 20 users under the `name` and `email` keys. A payload such as `%' OR 1=1 -- -` also bypasses the filter. The Laravel stack precedent that the query builder binds values does not apply, because this code uses `DB::select()` with interpolated input. Verification checked `routes/api.php` (the only guard is `auth:sanctum`) and the request validation (no character restriction); neither stops the input.
**Confidence:** High
**Fix:** Go back to bound parameters. For example: `User::query()->where(fn ($q) => $q->where('name', 'like', "%{$term}%")->orWhere('email', 'like', "%{$term}%"))->orderBy('name')->limit(20)->get(['id', 'name', 'email'])`. If raw SQL is required, use `DB::select('... LIKE ? OR email LIKE ? ...', ["%{$term}%", "%{$term}%"])`. Optionally escape `%` and `_` in the term.

### Architecture — Suggestion

**Location:** `app/Http/Controllers/UserSearchController.php:19-21`
**Issue:** The rewrite removes the only use of `User`, so `use App\Models\User;` (line 5) is now an unused import. The raw query also drops the Eloquent approach the project used before.
**Evidence:** `User` is not referenced anywhere in the controller after the change → dead import, and the controller no longer goes through the model.
**Confidence:** High
**Fix:** Restoring the query builder (see the Critical finding) makes the import used again. Otherwise remove it.

## Needs human verification

### Privacy/Compliance — Warning

**Location:** `app/Http/Controllers/UserSearchController.php:20`
**Issue:** The search now matches on `email` as well as `name`. Any authenticated user can look up accounts by an email fragment, and the full email is returned.
**Evidence:** A user sends `q=@competitor.com`, or `q=jane.doe@corp` to confirm a specific address is registered → the endpoint lists the matching accounts with their emails. Before this change, emails were only reachable through name matches. A person must check whether every authenticated user is meant to be able to search by email, or whether this needs a policy check or rate limiting. `routes/api.php` shows only `auth:sanctum`, and the controller has no authorization call.
**Confidence:** Medium
**Fix:** Confirm the product intent. If it is unintended, restrict email search to authorized roles (policy or gate) and add throttling to the route.

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

**Verification:** 2 Critical/Warning candidates checked, 0 refuted.

**Review effort:** 2/5 — up to 50 changed lines in 2 files; personal data.
**Relevant tests:** changed — `tests/Feature/UserSearchTest.php` adds `test_it_finds_users_by_email`, and the existing name test still covers name search. Neither test sends quotes or SQL metacharacters, LIKE wildcards, or an unauthenticated request. Execution: not run.
**Look first:** `app/Http/Controllers/UserSearchController.php` (SQL injection through the interpolated term, lines 18-21), `tests/Feature/UserSearchTest.php` (no test would catch the injection).
**Ready to merge:** No — 1 Critical finding must be fixed before merging.

## Audit

**Files reviewed:** 2 of 2 changed files: `app/Http/Controllers/UserSearchController.php`, `tests/Feature/UserSearchTest.php`.
**Read for context:** `composer.json`, `routes/api.php`, `skill:references/api-design.md`, `skill:references/intent.md`, `skill:references/privacy.md`, `skill:stacks/laravel.md`.
**Checked with no findings:** Performance, Tests/Coverage, Code & File Size, Potential Bugs, API Design, Stack-Specific.
**Not verified:** nothing.
