# Pest PHP — Code Review Checklist

> Load when project uses Pest (check `composer.json` for `pestphp/pest`). Detect version for version-specific rules.

## Test Structure

- **Pest syntax only**: all tests use `it()` / `test()` + `expect()` — no PHPUnit-style `$this->assert*` in Pest files
- **Test organization**: unit tests in `tests/Unit/`, feature tests in `tests/Feature/`, browser tests in `tests/Browser/`
- **No test removal without approval**: tests are core application code; deletion requires explicit justification
- **`php artisan make:test --pest`**: tests generated via artisan, not created manually

## Assertions

- **Specific response assertions**: named helpers used instead of generic `assertStatus()`:

  | Use | Instead of |
  |-----|-----------|
  | `assertSuccessful()` | `assertStatus(200)` |
  | `assertNotFound()` | `assertStatus(404)` |
  | `assertForbidden()` | `assertStatus(403)` |
  | `assertUnauthorized()` | `assertStatus(401)` |
  | `assertNoContent()` | `assertStatus(204)` |

- **`assertModelExists()`**: used for model persistence assertions over raw `assertDatabaseHas()`
- **Meaningful assertions**: tests assert behavior, not implementation; no `expect(true)->toBeTrue()` as a placeholder

## Datasets

- **Datasets for repetition**: validation rules, multiple similar inputs, boundary conditions use `->with([...])`; not copy-pasted test blocks
- **Named dataset entries**: dataset keys describe the case (`'valid email' => ...`) to produce readable failure messages

## Mocking

- **Import before use**: `use function Pest\Laravel\mock;` imported before calling `mock()` — missing import causes a silent fatal
- **Fakes after factories**: `Event::fake()`, `Mail::fake()`, etc. called after factory setup, not before — otherwise model observers/events are silenced during creation

## Database

- **`LazilyRefreshDatabase`**: preferred over `RefreshDatabase` for large test suites (speed); `RefreshDatabase` only when full reset per test is required
- **`recycle()`**: used to share relationship instances across related factories to avoid orphaned records and N+1 in test setup

## Browser Tests (Pest 4)

- **Location**: browser tests in `tests/Browser/`
- **`assertNoJavaScriptErrors()`**: called on every browser test — JS errors caught before they reach production
- **`assertNoConsoleLogs()`**: called alongside `assertNoJavaScriptErrors()` in smoke tests
- **Smoke test pattern**: `visit(['/route1', '/route2'])->assertNoJavaScriptErrors()->assertNoConsoleLogs()`
- **Multi-device**: viewport and device specified when UI is responsive; not just desktop tested

## Architecture Tests

- **`arch()` used**: project enforces architectural constraints via `arch()` tests when the codebase has clear layer boundaries
- **Suffixes enforced**: controller suffix, service suffix, etc. enforced via `toHaveSuffix()`
- **No dependencies**: lower layers do not depend on higher layers — `toUse()` / `not->toUse()` assertions present

## Test Isolation

- **No test-to-test dependencies**: tests pass in any order; no shared mutable state between tests
- **No real HTTP calls**: external services mocked or faked; `Http::preventStrayRequests()` active in test suite
- **No real queues**: `Queue::fake()` used in tests that dispatch jobs; not running actual workers

## Common Pitfalls

- `assertStatus(200)` instead of `assertSuccessful()` — obscures intent
- `mock()` called without `use function Pest\Laravel\mock;` import — silent fatal
- `Event::fake()` before factory creation — silences model event listeners, hiding real behavior
- No `assertNoJavaScriptErrors()` in browser tests — JS errors go undetected
- Dataset not used for validation rule tests — copy-paste test blocks drift out of sync
- `RefreshDatabase` on every test in a large suite — unnecessarily slow
- `expect(true)->toBeTrue()` as placeholder assertion — test always passes, covers nothing

## Precedents

- **`RefreshDatabase` rolls back each test's transactional writes**: tests that use `RefreshDatabase` (in the test file or through `tests/Pest.php`) run inside a transaction on each connection in `$connectionsToTransact` (the default connection when it is not set), and that transaction is rolled back afterward, so writes to transactional tables made inside it do not reach the next test. Do not report data from one test leaking into the next when those writes stay inside that transaction. **Exception:** database connections not listed in `$connectionsToTransact`, test files outside the directories that `tests/Pest.php` binds to `RefreshDatabase`, tables on a non-transactional storage engine such as MySQL `MyISAM`, whose writes a rollback does not undo, MySQL statements that commit implicitly, such as `ALTER TABLE` or `TRUNCATE`, and writes made through another connection or another process (a queue worker, a spawned command, or an HTTP request to a running server), which the test's transaction does not contain.
- **Laravel fakes reset between tests**: Laravel's base `TestCase` boots a fresh application for every test, so `Queue::fake()`, `Mail::fake()`, `Event::fake()` and `Http::fake()` do not carry over. Do not report a missing cleanup of these fakes. **Exception:** static properties and other global state outside the service container, and Pest tests that do not extend Laravel's `TestCase`.
