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
- **Related data**: without lazy loading, a navigation that the query does not `Include` stays `null` or empty, so code that reads it gives a wrong result without an error. With lazy-loading proxies on (`UseLazyLoadingProxies`), reading it in a loop runs one query per row.
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

- **Authorization gaps**: `[AllowAnonymous]` bypasses every authorization attribute and policy of that endpoint, including one on its controller. A new controller or minimal API endpoint without `[Authorize]` or `RequireAuthorization()` is public. **Not a finding:** an endpoint without authorization attributes when the app sets a `FallbackPolicy` that requires authenticated users.
- **Over-posting**: binding a request body or form directly to an EF entity and saving it lets a client set properties that the UI never sends, such as `IsAdmin` or `OwnerId`. Bind an input model that has only the fields the client may set.
- **Unsafe deserialization**: `BinaryFormatter` (obsolete, and throwing on .NET 9 and later), `NetDataContractSerializer`, `LosFormatter`, `ObjectStateFormatter`, and Newtonsoft.Json with any `TypeNameHandling` other than `None`, on untrusted data, can run code. **Not a finding:** `System.Text.Json`, whose polymorphic deserialization (.NET 7+) accepts only derived types that the contract declares, such as with `[JsonDerivedType]`.
- **Paths from input**: `Path.Combine(root, name)` returns `name` when it is rooted and keeps `..`. Resolve with `Path.GetFullPath(...)` and check that the result starts with the root followed by a directory separator.

## Nullable Reference Types

- **Annotations are compile-time only**: a non-nullable property filled by model binding, JSON deserialization, EF Core or reflection can still hold `null` at run time, and the `!` operator silences the warning without a check. `System.Text.Json` enforces non-nullable annotations only with `RespectNullableAnnotations` (.NET 9+). **Not a finding:** a missing null check on a value that comes only from code compiled with `<Nullable>enable</Nullable>`, where the compiler already warns about a possible `null`.

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
- `[AllowAnonymous]` and the fallback policy: https://learn.microsoft.com/en-us/aspnet/core/security/authorization/simple, https://learn.microsoft.com/en-us/aspnet/core/security/authorization/secure-data
- Over-posting: https://learn.microsoft.com/en-us/aspnet/core/data/ef-mvc/crud
- `BinaryFormatter`: https://learn.microsoft.com/en-us/dotnet/standard/serialization/binaryformatter-security-guide; `TypeNameHandling`: https://www.newtonsoft.com/json/help/html/T_Newtonsoft_Json_TypeNameHandling.htm; `System.Text.Json` polymorphism: https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/polymorphism
- `Path.Combine`: https://learn.microsoft.com/en-us/dotnet/api/system.io.path.combine
- Nullable reference types and `RespectNullableAnnotations`: https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references, https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/nullable-annotations

## Precedents

- **Razor encodes output**: Razor `@expression` and Blazor `@value` output of ordinary untrusted string values is HTML-encoded by default, which makes them safe in HTML text and in quoted, non-executable attribute values. Do not report XSS for such string values rendered that way. **Exception:** `@Html.Raw(...)`, any `IHtmlContent` implementation, including `HtmlString`, custom or helper-produced content and `HtmlContentBuilder.AppendHtml(...)`, which Razor writes through its own `WriteTo` without encoding, so its producer must establish its safety, Blazor `MarkupString` values, other values that render their own markup, user-controlled URLs in `href`, `src` or `action`, where encoding does not stop a `javascript:` URL, attributes whose decoded value is parsed as HTML, such as `srcdoc`, unquoted attribute values, and values written into `<script>` blocks or event-handler attributes, where HTML encoding is not JavaScript encoding (use `JavaScriptEncoder` or JSON serialization there).
- **EF Core parameterizes queries**: LINQ queries and the interpolated methods `FromSqlInterpolated` (EF Core 3.0+), `ExecuteSqlInterpolated` and `FromSql` (EF Core 7.0+, whose only overload takes a `FormattableString`) turn values into parameters. Do not report SQL injection for them. **Exception:** `FromSqlRaw`, `ExecuteSqlRaw` and `SqlQueryRaw` with SQL built by concatenation or string interpolation, and `FromSql` or `ExecuteSqlCommand` on EF Core before 3.0 (check the `Microsoft.EntityFrameworkCore` version), where both also accept a plain string and send it as raw SQL, so `FromSql("SELECT … " + id)` or an interpolated string stored in a variable and passed to either is injectable.
