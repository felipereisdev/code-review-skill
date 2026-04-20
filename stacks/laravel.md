# Laravel — Code Review Checklist

> Check sibling files for existing patterns before flagging any violation (see Consistency Check step).

## Eloquent & Database

- **Eloquent best practices**: use scopes, accessors, mutators; avoid raw queries unless necessary
- **Model casting**: casts defined for dates, enums, booleans, and serialized objects via the `casts()` method
- **Chunking large datasets**: `chunk()`, `cursor()`, or `lazy()` used when processing large volumes of records to avoid memory exhaustion
- **Aggregate helpers**: `withCount()`, `withSum()`, `withAvg()` used instead of loading collections just to aggregate
- **preventLazyLoading**: `Model::preventLazyLoading()` enabled in development to catch N+1 at dev time
- **Soft deletes**: `withTrashed()` / `onlyTrashed()` used intentionally; deleted records not accidentally leaked in queries
- **Select only needed columns**: `SELECT *` avoided; specify columns explicitly in complex queries
- **`whereBelongsTo()`**: used for cleaner relationship queries instead of manual `where('model_id', $model->id)`
- **`whereIn + pluck`**: preferred over `whereHas()` for better index usage when filtering by related model IDs

## Advanced Query Patterns

- **`addSelect()` subqueries**: used over eager-loading entire has-many relations just to get a single aggregate value
- **Dynamic relationships via subquery**: subquery FK + `belongsTo` used to avoid N+1 when accessing a single "latest" or "first" related record
- **Conditional aggregates**: `CASE WHEN` in `selectRaw()` used instead of multiple count queries
- **`setRelation()`**: used to prevent circular N+1 when manually constructing relationships
- **Compound indexes**: match `orderBy` column order; correlated subqueries in `orderBy` for has-many sorting (avoid joins that multiply rows)

## Caching

- **`Cache::remember()`**: used over manual get/put pairs
- **`Cache::flexible()`**: used for stale-while-revalidate on high-traffic data that can serve slightly stale content
- **`Cache::memo()` / `once()`**: avoid redundant cache hits within a single request; `once()` for per-object memoization
- **Cache tags**: used to invalidate groups of related cache entries atomically
- **`Cache::add()`**: used for atomic conditional writes (set if not exists)
- **`Cache::lock()`**: used for race conditions; `lockForUpdate()` for DB-level locking
- **Failover stores**: `Cache::store()` with fallback configured in production

## HTTP Client

- **Explicit timeouts**: every outbound HTTP call has `timeout()` and `connectTimeout()`; no fire-and-forget calls without timeouts
- **Retry with backoff**: `retry()` with exponential delays for external APIs; non-retriable errors (4xx) not retried
- **Status check**: `throw()` or explicit status check after every response; no silent failures
- **`Http::pool()`**: used for concurrent independent HTTP requests instead of sequential calls
- **Testing**: `Http::fake()` + `Http::preventStrayRequests()` in all tests touching HTTP calls

## Queues & Jobs

- **`retry_after` > `timeout`**: `retry_after` in queue config must exceed the job's `$timeout`; prevents duplicate processing
- **Exponential backoff**: `backoff()` returns `[1, 5, 10]` or similar; not relying on uniform retries
- **`ShouldBeUnique`**: implemented on jobs that must not run concurrently; `WithoutOverlapping::untilProcessing()` for overlap prevention
- **`failed()` always present**: every job implements `failed(Throwable $e)`; failures not silently discarded
- **`retryUntil()` + `$tries = 0`**: when using `retryUntil()`, set `$tries = 0` to avoid early bail-out
- **`RateLimited` middleware**: used for jobs calling external APIs; `Bus::batch()` for related parallel jobs
- **`Bus::chain()`**: used correctly for sequential job dependencies

## Events & Notifications

- **`ShouldDispatchAfterCommit`**: events dispatching side effects (emails, notifications, external calls) use this to prevent firing before the DB transaction commits
- **Event discovery**: manual registration avoided; `event:cache` run in production
- **`ShouldQueue`**: notifications and mailables are queued; synchronous sending only for critical flows
- **`assertQueued()`**: used in tests for queued mailables/notifications, not `assertSent()`

## Controllers & Actions

- **Form Requests**: validation in Form Request classes; `authorize()` not returning `true` by default on all protected requests
- **Single Action Controllers**: `__invoke` controllers for simple single-purpose actions
- **Action classes**: invokable Actions for reusable business logic that doesn't belong to a Service
- **Controller methods**: under 10 lines; complex logic extracted to services or actions

## Collections & Helpers

- **Collection pipelines**: `map`, `filter`, `reduce`, `groupBy` used over manual loops
- **`cursor()` vs `lazy()`**: `cursor()` for memory-efficient iteration without relationships; `lazy()` when relationship loading needed; `lazyById()` when updating records while iterating
- **`toQuery()`**: converts a collection back to a query builder for bulk operations (update/delete) without loading models
- **Laravel helpers**: `Str::` and `Arr::` over raw PHP functions; `Str::of()`, `$request->string()` for fluent string operations

## Security & Auth

- **Policy enforcement**: `$this->authorize()` or `Gate::authorize()` called in controllers; not relying solely on route middleware for authorization
- **Sanctum token scopes**: API tokens issued with minimal required abilities; abilities checked explicitly
- **Mass assignment**: `$fillable` or `$guarded` defined on every model
- **`$request->validated()`**: only validated data used — never `$request->all()` or `$request->input()` without validation

## Validation & Forms

- **Form Request classes**: `$request->validated()` only — never `$request->all()`
- **`Rule::when()`**: conditional validation rules; not inline ternaries
- **Array notation**: `['required', 'email']` for new code; follow existing convention if project uses string pipes
- **`after()` hook**: used instead of `withValidator()` for post-validation logic

## Testing

- **`LazilyRefreshDatabase`**: preferred over `RefreshDatabase` for speed in large test suites
- **`assertModelExists()`**: over raw `assertDatabaseHas()` when asserting model persistence
- **Factory states**: existing states reused; not manually configuring models in every test
- **Fakes after factories**: `Event::fake()`, `Mail::fake()`, etc. called after factory setup (not before), otherwise factory observers/events may be silenced
- **`recycle()`**: shares relationship instances across related factories to avoid orphaned records
- **`withoutExceptionHandling()`**: used in tests that need to inspect the real exception
- **`Http::fake()` + `preventStrayRequests()`**: always in tests touching external HTTP

## Routing & Config

- **Route model binding**: used instead of manual `find()` + 404 checks
- **Scoped bindings**: `->scopeBindings()` for nested resources
- **`env()` only in config files**: application code accesses values via `config()` — never `env()` directly
- **Named routes**: `route()` helper used; no hardcoded URL strings
- **`App::environment()`**: used for environment checks; not `app()->environment()` string comparison via `env()`

## Migrations

- **`constrained()`**: all foreign keys use `constrained()` for consistent cascades and index creation
- **One concern per migration**: DDL and DML never mixed in the same migration
- **Defaults mirrored in model**: column defaults in migration mirrored in `$attributes` array on the model
- **Reversible `down()`**: `down()` correctly undoes `up()` without data loss; forward-fix migrations for intentionally irreversible changes
- **Indexes added in migration**: not as an afterthought; never added manually in production without migration

## Architecture

- **Service layer**: complex business logic in services; controllers delegate, not implement
- **API Resources**: responses formatted via `JsonResource`; no raw `$model->toArray()` in controllers
- **Events & Listeners**: side effects triggered via events; not inline in controllers or services
- **Dependency injection**: constructor injection; facades avoided in business logic when testability matters
- **`defer()`**: post-response work deferred; `Context` for request-scoped shared data; `Concurrency::run()` for parallel execution
- **Blade/views**: no business logic in templates; use view composers or components

## Common Pitfalls

- `env()` called directly in application code instead of `config()`
- `$request->all()` used instead of `$request->validated()`
- `authorize()` in Form Request returns `true` unconditionally
- Job `$timeout` exceeds `retry_after`, causing duplicate processing
- Events dispatched inside DB transactions without `ShouldDispatchAfterCommit`
- `Http::fake()` missing in tests → real HTTP calls in CI
- Fakes set up before factories, silencing model observers
- `whereHas()` used where `whereIn + pluck()` would use an index
- `Cache::remember()` without tags when cache invalidation is needed
