# Laravel — Code Review Checklist

## Eloquent & Database
- **Eloquent best practices**: use scopes, accessors, mutators; avoid raw queries unless necessary
- **Model casting**: casts defined for dates, enums, booleans, and serialized objects via the `casts()` method
- **Chunking large datasets**: `chunk()`, `cursor()`, or `lazy()` used when processing large volumes of records to avoid memory exhaustion
- **Aggregate helpers**: `withCount()`, `withSum()`, `withAvg()` used instead of loading collections just to aggregate
- **preventLazyLoading**: `Model::preventLazyLoading()` enabled in development to catch N+1 at dev time
- **Soft deletes**: `withTrashed()` / `onlyTrashed()` used intentionally; deleted records not accidentally leaked in queries

## Controllers & Actions
- **Form Requests**: validation logic lives in Form Request classes, not controllers; `authorize()` method implemented correctly — not returning `true` by default on all protected requests
- **Single Action Controllers**: `__invoke` controllers used for simple, single-purpose actions instead of generic multi-method controllers
- **Action classes**: reusable business logic that doesn't belong to a Service extracted to invokable Action classes

## Collections & Helpers
- **Collection pipelines**: `map`, `filter`, `reduce`, `groupBy`, etc. used instead of manual loops where clearer
- **Laravel helpers**: `Str::` and `Arr::` helpers used instead of raw PHP functions when they offer more clarity or safety

## Queues & Jobs
- **Unique jobs**: `ShouldBeUnique` implemented on jobs that must not be enqueued more than once simultaneously
- **Job batching & chaining**: `Bus::chain()` / `Bus::batch()` used correctly when jobs have sequential or parallel dependencies
- **Job configuration**: `$tries`, `$timeout`, and `backoff()` defined explicitly; not relying solely on global defaults

## Security & Auth
- **Policy enforcement**: `$this->authorize()` or `Gate::authorize()` called in controllers; not relying solely on route middleware
- **Sanctum token scopes**: API tokens issued with minimal required abilities; abilities checked explicitly in guarded routes

## Testing
- **withoutExceptionHandling**: used in tests that need to inspect the real exception, not the formatted error response
- **Database assertions**: `assertDatabaseHas`, `assertDatabaseMissing`, `assertSoftDeleted` used for persistence assertions
- **Factory states**: existing factory states reused instead of manually configuring models in every test

## Routing & Config
- **Route model binding**: used where appropriate instead of manual `find()` + 404 checks
- **Config & env**: no `env()` calls outside of config files; all config accessed via `config()`
- **Named routes**: `route()` helper used with named routes; no hardcoded URL strings

## Architecture
- **Service layer**: complex business logic extracted to services, not bloating controllers
- **API Resources**: responses use API Resources/Transformers for consistent formatting
- **Blade/views**: no business logic in Blade templates; use view composers or components
- **Events & Listeners**: side effects (emails, notifications, logs) triggered via events, not inline
- **Dependency injection**: use constructor injection via the service container; avoid facades in business logic when testability matters
- **Migrations**: schema changes use migrations; migrations are reversible (`down` method)
