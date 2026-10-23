### Security — Critical

**File:** `app/Http/Controllers/UserSearchController.php:19-21`
**Issue:** The raw `DB::select()` query interpolates user input (`$term`) straight into the SQL string, so it is open to SQL injection. The `max:100` and `string` validation rules don't stop it. For example, `q=' UNION SELECT id, password, remember_token FROM users -- ` would leak other columns. Any authenticated user can exploit it. The original Eloquent query was safe, so this change introduces the vulnerability.
**Fix:** Go back to the query builder, or use bound parameters:
```php
$users = User::query()
    ->where(fn ($q) => $q
        ->where('name', 'like', "%{$term}%")
        ->orWhere('email', 'like', "%{$term}%"))
    ->orderBy('name')
    ->limit(20)
    ->get(['id', 'name', 'email']);
```
If raw SQL is truly needed, use `DB::select('... LIKE ? OR email LIKE ? ...', ["%{$term}%", "%{$term}%"])`.

### Security — Warning

**File:** `app/Http/Controllers/UserSearchController.php:20`
**Issue:** The endpoint now searches by `email` and returns it to any authenticated user. That lets any user enumerate other users' email addresses by prefix or substring. There is no rate limit and no authorization check. LIKE wildcards (`%`, `_`) in the input are also not escaped.
**Fix:** Confirm that exposing emails is intended. If it is, add a policy or `Gate::authorize()` check and throttling (`throttle:` middleware). Consider escaping `%` and `_` in the term.

### Stack-Specific (Laravel) — Warning

**File:** `app/Http/Controllers/UserSearchController.php:19`
**Issue:** The change drops Eloquent for a raw query, which goes against the Laravel checklist ("avoid raw queries unless necessary"). The `use App\Models\User;` import is now unused, which is dead code. The result also changes from a collection of `User` models to an array of `stdClass` objects. Nothing here needs raw SQL.
**Fix:** Use Eloquent as shown above, which also uses the `User` import. Consider an API Resource for the response.

### Potential Bugs — Suggestion

**File:** `app/Http/Controllers/UserSearchController.php:20`
**Issue:** The `name LIKE ... OR email LIKE ...` condition is written without grouping. It is correct today, but adding another `AND` condition later could change the logic without anyone noticing. Leading-wildcard `LIKE` on `email` can't use an index. That is acceptable for a table of this size but worth knowing about.
**Fix:** Group the conditions with a closure in the query builder. Consider a full-text index if the table grows.

### Tests/Coverage — Warning

**File:** `tests/Feature/UserSearchTest.php:22-31`
**Issue:** The new test only covers the happy path for an email match. It has no test for SQL injection or special characters (for example a quote in `q`), no test that a non-matching term returns an empty result, and no test for the validation failures (missing `q`, or `q` over 100 characters). It also searches as the same user it creates, so it doesn't show that other users are found. A test with a quote in the input would have caught the injection.
**Fix:** Add tests for a term containing `'`, for no match, for validation errors, and for an unauthenticated request returning 401.

### What Was Done Well

- Input validation is in place (`required`, `string`, `max:100`), and `->limit(20)` keeps the result set bounded.
- The route is protected by `auth:sanctum`.
- A feature test was added alongside the new email-search behavior.

## Summary

| Category              | Critical | Warning | Suggestion | N/A |
|-----------------------|----------|---------|------------|-----|
| Security              | 1        | 1       | 0          |     |
| Performance           | 0        | 0       | 0          |     |
| Tests/Coverage        | 0        | 1       | 0          |     |
| Architecture          | 0        | 0       | 0          |     |
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
| Stack-Specific        | 0        | 1       | 0          |     |
| **Total**             | **1**    | **3**   | **1**      |     |

**Verdict:** Do not merge until the SQL injection is fixed.
