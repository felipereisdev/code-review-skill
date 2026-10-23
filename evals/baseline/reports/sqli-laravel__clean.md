# Code Review: staged changes (`git diff --cached`)

**Scope:** `UserSearchController.php` and `UserSearchTest.php`. The stack is Laravel 11 on PHP 8.2 with PHPUnit. I loaded `stacks/laravel.md`. No other stack or pattern files apply. I did not run the tests.

## What Was Done Well
- The `orWhere` is wrapped in a closure, so the name/email condition is grouped. Any scope or constraint added to the query later won't be bypassed by operator precedence.
- Input validation is kept (`required|string|max:100`). Results are capped with `limit(20)` and only `id`, `name` and `email` are selected.
- Values are bound as parameters, so there is no SQL injection.
- A feature test was added for the new email path, and it follows the style of the existing name test.

## Findings

### Security — Warning

**File:** `app/Http/Controllers/UserSearchController.php:19-20`
**Issue:** Email is now a search key, so any authenticated user can probe which email addresses exist. For example, they can query `q=a`, `q=ab` and so on, or search for a known address or domain. The route has only `auth:sanctum`, with no policy check and no throttling. Returning `email` before was a smaller exposure than making it searchable. This is user data under Privacy/Compliance, but I'm filing it once here.
**Fix:**
- Confirm that every authenticated user is meant to be able to look up other users by email. If not, add a policy or `Gate::authorize()`, or limit the search to the caller's tenant or team.
- Add `throttle:` middleware to the route.
- Consider requiring a longer minimum query for email matches, for example `min:3`.

### Potential Bugs — Suggestion

**File:** `app/Http/Controllers/UserSearchController.php:19-20`
**Issue:** The user input is concatenated into the LIKE pattern without escaping `%` and `_`. A query of `_` or `%` matches every row. This was already true for `name`, but it now applies to `email` too. `_` is very common in email local parts, such as `john_doe@…`, so searches for them will return false positives.
**Fix:** Escape the wildcards before building the pattern, for example `addcslashes($validated['q'], '%_\\')`. Compute the pattern once in a `$term` variable. That also removes the duplicated `'%'.$validated['q'].'%'` expression.

### Performance — Suggestion

**File:** `app/Http/Controllers/UserSearchController.php:19-20`
**Issue:** `LIKE '%…%'` with a leading wildcard can't use a B-tree index. The `OR` across two columns makes it worse, because `email` probably has a unique index that is now unused. On a large `users` table this is a full scan on every keystroke, if the UI uses typeahead. I couldn't check the migrations (the repo has no `database/` directory). The ordering by `name` is also unindexed.
**Fix:** If the table is large, use a prefix match (`'term%'`) for email, or a full-text index or a search engine. Otherwise accept the cost and add rate limiting.

### Tests/Coverage — Warning

**File:** `tests/Feature/UserSearchTest.php:23-31`
**Issue:**
- The new test creates only one user, who is also the authenticated one. It would pass even if the query returned every user, or if the filter were broken. It does not show that non-matching users are excluded.
- It does not check the result content, only `assertJsonCount(1)`.
- Nothing covers the `OR` behaviour (a name-only match and an email-only match returning together), a query with no results, validation failures (missing `q` or `q` over 100 characters), or unauthenticated access (401).
**Fix:** Create a second, non-matching user, and assert `assertJsonCount(1)` plus `assertJsonFragment(['email' => 'ada@example.com'])` or `assertJsonPath('0.email', …)`. Add cases for no match, `_` and `%` literals, 422 on validation, and 401.

### Architecture — Suggestion

**File:** `app/Http/Controllers/UserSearchController.php:12-30`
**Issue:**
- Validation is inline rather than in a Form Request, and the response is raw JSON rather than an API Resource (the Laravel checklist prefers both). The controller is a single-action `__invoke`, which matches the checklist.
- The method is about 18 lines, which is within limits, though the checklist target for controller methods is under 10.
**Fix:** Optional. I couldn't see sibling controllers to confirm the established convention, so I'm not raising this above Suggestion. If the project uses Form Requests elsewhere, move validation into one. Extracting the search into a `User` query scope such as `scopeSearch()` would also keep the controller thin.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 0        | 1       | 0          |     |
| Performance           | 0        | 0       | 1          |     |
| Tests/Coverage        | 0        | 1       | 0          |     |
| Architecture          | 0        | 0       | 1          |     |
| Code & File Size      | 0        | 0       | 0          |     |
| Potential Bugs        | 0        | 0       | 1          |     |
| Accessibility         |          |         |            | N/A |
| Observability         | 0        | 0       | 0          |     |
| API Design            | 0        | 0       | 0          |     |
| Resilience            |          |         |            | N/A |
| DB Migrations         |          |         |            | N/A |
| Concurrency           |          |         |            | N/A |
| i18n                  |          |         |            | N/A |
| Privacy/Compliance    | 0        | 0       | 0          |     |
| Architecture Patterns |          |         |            | N/A |
| Stack-Specific        | 0        | 0       | 0          |     |
| **Total**             | **0**    | **2**   | **3**      |     |

There are no blockers. The two Warnings are the email enumeration exposure and the weak test. I'd fix both soon, ideally before merging, since the change widens what any logged-in user can discover.
