# .NET / C# — Code Review Checklist

> Check sibling projects for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A diagnostic that the compiler or an analyzer configured in the repository already reports, such as a nullable warning under `<Nullable>enable</Nullable>` with `TreatWarningsAsErrors`, is not a finding. An item that depends on a version names the `<TargetFramework>` or the package version that it needs.

## Async

- **Blocking on tasks**: `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` on an unfinished task deadlocks when a single-threaded `SynchronizationContext` waits for the same thread, as in WPF, WinForms and ASP.NET on .NET Framework. ASP.NET Core has no such context, so there it does not deadlock, but each call holds a thread-pool thread, and under load the pool starves and every request slows down. **Not a finding:** `.Result` on a task that is already complete, such as after `await Task.WhenAll(...)`.
- **`async void`**: an exception thrown from an `async void` method cannot be caught by its caller and, raised on the thread pool, crashes the process; the caller also cannot wait for it to finish. **Not a finding:** event handlers, which must return `void`, when they catch their own exceptions.
- **Work after the response**: `Task.Run` or an unawaited task that keeps using request-scoped services, such as a `DbContext`, or the `HttpContext` after the request ends fails with `ObjectDisposedException` or reads invalid request state. Hand the work to a hosted service that creates its own scope with `IServiceScopeFactory`.

**Bad** — blocks a thread-pool thread for each request until the query finishes:

```csharp
public IActionResult Get(int id)
{
    var order = _orders.FindAsync(id).Result;
    return Ok(order);
}
```

**Good** — the thread returns to the pool while the query runs:

```csharp
public async Task<IActionResult> Get(int id)
{
    var order = await _orders.FindAsync(id);
    return Ok(order);
}
```

## Dependency Injection and Disposal

- **Captive dependencies**: a singleton that receives a scoped service, such as a `DbContext`, in its constructor keeps the first instance for the life of the app and shares it across concurrent requests. The default host checks for this only in the Development environment, so the app starts normally in production. **Not a finding:** a singleton that creates a scope per operation with `IServiceScopeFactory`.
- **`HttpClient` lifetime**: `new HttpClient()` per request, even inside `using`, can exhaust sockets under load, and a single long-lived `HttpClient` does not see DNS changes unless `SocketsHttpHandler.PooledConnectionLifetime` is set. **Not a finding:** clients from `IHttpClientFactory`, and a shared client with `PooledConnectionLifetime`.
- **Disposal**: an `IDisposable` or `IAsyncDisposable` that the code creates per call, such as a `Stream`, a `SqlConnection` or a `CancellationTokenSource`, without `using` or `await using` keeps its handle, connection or timer until the garbage collector finalizes it. **Not a finding:** services resolved from the DI container, which the container disposes.

## EF Core and LINQ

- **Client-side filtering**: calling `AsEnumerable()` or `ToList()`, or passing the query on as `IEnumerable<T>`, before `Where`, `OrderBy` or `Take` loads every row and filters in memory. Keep the query as `IQueryable<T>` until it is filtered.
- **Concurrent use of a `DbContext`**: a `DbContext` is not thread-safe. Starting two queries on the same context at once, for example with `Task.WhenAll`, throws `InvalidOperationException` ("A second operation was started on this context instance before a previous operation completed"). Await them one after the other, or use one context per operation from `IDbContextFactory<TContext>`.
- **Related data**: a navigation is populated only when the query loads it: through `Include` or `ThenInclude`, through a navigation configured with `AutoInclude()` in the model, as an owned type that loads with its owner, or by explicit loading. Code that reads a navigation the query does not load gets `null` or an empty collection with no error. Relationship fix-up can also fill a collection with only the related entities already tracked in the context, so a collection can be partially populated without any sign of it. A `Select` projection that reads only the values it needs does not need the navigation loaded. With lazy-loading proxies on (`UseLazyLoadingProxies`), reading an unloaded navigation in a loop runs one query per row.
- **Untracked entities**: changes to entities loaded with `AsNoTracking()` are not saved by `SaveChanges()` unless the code attaches or updates them.
- **Lost updates**: a read-modify-write of a row that concurrent requests change, with no concurrency token (`[ConcurrencyCheck]` or a `rowversion` property), keeps only the last write. With a token, `SaveChanges()` throws `DbUpdateConcurrencyException`, which the code must handle.
- **Multiple enumeration**: enumerating an `IQueryable<T>` twice, for example `Count()` and then `foreach`, runs the query twice and can see different rows. **Not a finding:** enumerating a materialized list twice.

**Bad** — loads every order, then filters in memory:

```csharp
var orders = _db.Orders
    .AsEnumerable()
    .Where(o => o.CustomerId == customerId)
    .ToList();
```

**Good** — the filter is translated to SQL:

```csharp
var orders = _db.Orders
    .Where(o => o.CustomerId == customerId)
    .ToList();
```

## ASP.NET Core Security

- **Authorization gaps**: a controller action or minimal API endpoint is public unless authorization comes from elsewhere, so report it only when its data or action needs an authenticated user. `[AllowAnonymous]` on such an endpoint bypasses every authorization attribute and policy that applies to it, including one on its controller, on a base controller or set by a convention. Other authorization that protects the endpoint: `[Authorize]` inherited from a base controller (`AuthorizeAttribute` is `Inherited = true`), a global `AuthorizeFilter` added to MVC or Razor Pages options, `RequireAuthorization()` on the endpoint or on `MapControllers`, `MapRazorPages` or a route group, and a `FallbackPolicy` that requires authenticated users, which applies to endpoints that have no other authorization metadata. **Not a finding:** an endpoint that is meant to be public, such as login, a health check or a page marked `[AllowAnonymous]` that serves public content, and any endpoint that one of the mechanisms above protects.
- **Over-posting**: binding a request to an EF entity and saving it lets a client set a property that the code does not intend the client to write, such as `IsAdmin` or `OwnerId`, when that property binds and is saved. An effective allowlist limits what binds: a `[Bind(...)]` include list on the action parameter, or a `TryUpdateModelAsync` call with an explicit property list. `[BindNever]` on a property excludes it from model binding. Report the finding only when the unauthorized property actually binds and is persisted. These attributes do not protect a JSON body that `[FromBody]` reads through an input formatter, so `[BindNever]` does not stop a JSON client from setting that property. An input model that has only the fields the client may set is one remedy, not the only acceptable design.
- **Unsafe deserialization**: `BinaryFormatter`, `NetDataContractSerializer`, `LosFormatter` and `ObjectStateFormatter` on untrusted data can run code, and no type filter makes `BinaryFormatter` safe. The in-box `BinaryFormatter` throws on use from .NET 9 on, even with the settings that once enabled it. Newtonsoft.Json with a `TypeNameHandling` other than `None` on untrusted data is a finding when the types a client can name are consequential: no effective `SerializationBinder` restricts `$type` to a closed set of safe types. A binder that rejects every other type is a mitigation for that setting. **Not a finding:** `System.Text.Json`, whose polymorphic deserialization (.NET 7+) accepts only derived types that the contract declares, such as with `[JsonDerivedType]`.
- **Paths from input**: `Path.Combine(root, name)` returns `name` when it is rooted and keeps `..`. Resolve with `Path.GetFullPath(...)` and check that the result starts with the root followed by a directory separator.

## Nullable Reference Types

- **Annotations are compile-time only**: a non-nullable property filled by JSON deserialization, EF Core, reflection or a minimal-API body that the code does not validate can still hold `null` at run time, and the `!` operator silences the warning without a check. MVC model binding is different: with `<Nullable>enable</Nullable>`, it treats a non-nullable bound property as `[Required]`, so a missing value fails validation, and with `[ApiController]`, unless `SuppressModelStateInvalidFilter` is `true`, an invalid value gets an automatic HTTP 400 before the action runs. `System.Text.Json`'s `RespectNullableAnnotations` (.NET 9+) rejects an explicit `null` for a non-nullable member only, not a missing property, and does not cover top-level types, collection elements or generic members; use `required` or `[JsonRequired]` for presence. Validation that rejects `null` and whose failure stops the request before the action uses the value, such as `[Required]` under an automatic 400 or an action that returns on an invalid `ModelState`, or a validator that rejects the request, also protects the value. An attribute that only adds a `ModelState` error does not. **Not a finding:** a missing null check on a non-nullable property that MVC binds when `<Nullable>enable</Nullable>` is set and either `[ApiController]` applies without `SuppressModelStateInvalidFilter` or the action returns on an invalid `ModelState`, unless `SuppressImplicitRequiredAttributeForNonNullableReferenceTypes` is set; and a missing null check on a value that comes only from code compiled with `<Nullable>enable</Nullable>`, where the compiler already warns about a possible `null`.

## Conventions, not defects

- Where `ToList()` or `ToArray()` sits on in-memory data, LINQ query versus method syntax, `var` and expression-bodied members are style.
- A service lifetime (`Transient` or `Scoped` for a stateless service) is a finding only with the shared-state scenario of a captive dependency.
- Migration files are reviewed like any other changed code; their presence alone is not a finding.

## Sources

- Blocking calls, thread-pool starvation and `HttpContext` after the request: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/best-practices
- `async void`: https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/async-return-types
- Scope validation and disposal of services: https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection, https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection-guidelines
- Hosted services with scopes: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/host/hosted-services
- `HttpClient` guidelines: https://learn.microsoft.com/en-us/dotnet/fundamentals/networking/http/httpclient-guidelines
- `using` and disposal: https://learn.microsoft.com/en-us/dotnet/standard/garbage-collection/using-objects
- `DbContext` lifetime, threading and factories: https://learn.microsoft.com/en-us/ef/core/dbcontext-configuration/
- Client evaluation: https://learn.microsoft.com/en-us/ef/core/querying/client-eval
- Related data and lazy loading: https://learn.microsoft.com/en-us/ef/core/querying/related-data/
- Tracking: https://learn.microsoft.com/en-us/ef/core/querying/tracking
- Concurrency conflicts: https://learn.microsoft.com/en-us/ef/core/saving/concurrency
- `[AllowAnonymous]` and the fallback policy: https://learn.microsoft.com/en-us/aspnet/core/security/authorization/simple, https://learn.microsoft.com/en-us/aspnet/core/security/authorization/secure-data; `AuthorizeAttribute` (`Inherited = true`): https://learn.microsoft.com/en-us/dotnet/api/microsoft.aspnetcore.authorization.authorizeattribute
- Over-posting: https://learn.microsoft.com/en-us/aspnet/core/data/ef-mvc/crud
- `BinaryFormatter`: https://learn.microsoft.com/en-us/dotnet/standard/serialization/binaryformatter-security-guide; `TypeNameHandling`: https://www.newtonsoft.com/json/help/html/T_Newtonsoft_Json_TypeNameHandling.htm; `System.Text.Json` polymorphism: https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/polymorphism
- `Path.Combine`: https://learn.microsoft.com/en-us/dotnet/api/system.io.path.combine
- Nullable reference types and `RespectNullableAnnotations`: https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references, https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/nullable-annotations; MVC implicit required validation: https://learn.microsoft.com/en-us/aspnet/core/mvc/models/validation; `[ApiController]` automatic 400 and `SuppressModelStateInvalidFilter`: https://learn.microsoft.com/en-us/aspnet/core/web-api/

## Precedents

- **Razor encodes output**: Razor `@expression` and Blazor `@value` output of ordinary untrusted string values is HTML-encoded by default, which makes them safe in HTML text and in quoted, non-executable attribute values. Do not report XSS for such string values rendered that way. **Exception:** `@Html.Raw(...)`, any `IHtmlContent` implementation, including `HtmlString`, custom or helper-produced content and `HtmlContentBuilder.AppendHtml(...)`, which Razor writes through its own `WriteTo` without encoding, so its producer must establish its safety, Blazor `MarkupString` values, other values that render their own markup, user-controlled URLs in `href`, `src` or `action`, where encoding does not stop a `javascript:` URL, attributes whose decoded value is parsed as HTML, such as `srcdoc`, unquoted attribute values, and values written into `<script>` blocks or event-handler attributes, where HTML encoding is not JavaScript encoding (use `JavaScriptEncoder` or JSON serialization there).
- **EF Core parameterizes queries**: LINQ queries and the interpolated methods `FromSqlInterpolated` (EF Core 3.0+), `ExecuteSqlInterpolated` and `FromSql` (EF Core 7.0+, whose only overload takes a `FormattableString`) turn values into parameters. Do not report SQL injection for them. **Exception:** `FromSqlRaw`, `ExecuteSqlRaw` and `SqlQueryRaw` with SQL built by concatenation or string interpolation, and `FromSql` or `ExecuteSqlCommand` on EF Core before 3.0 (check the `Microsoft.EntityFrameworkCore` version), where both also accept a plain string and send it as raw SQL, so `FromSql("SELECT … " + id)` or an interpolated string stored in a variable and passed to either is injectable.
