# .NET / C# — Code Review Checklist

- **Async/await**: `async`/`await` used consistently; no `.Result` or `.Wait()` blocking calls on async methods
- **IDisposable**: disposable resources wrapped in `using` statements or properly disposed in `Dispose()` method
- **Nullable reference types**: nullable annotations used correctly; null checks present where needed
- **Dependency injection**: services registered with correct lifetime (`Transient`, `Scoped`, `Singleton`); no captive dependency issues
- **LINQ**: LINQ queries deferred correctly; `ToList()`/`ToArray()` called only when materialization is needed
- **Entity Framework**: no N+1 queries; `Include`/`ThenInclude` used for related data; migrations reviewed

## Precedents

- **Razor encodes output**: Razor `@expression` and Blazor `@value` output of ordinary untrusted string values is HTML-encoded by default, which makes them safe in HTML text and in quoted, non-executable attribute values. Do not report XSS for such string values rendered that way. **Exception:** `@Html.Raw(...)`, any `IHtmlContent` implementation, including `HtmlString`, custom or helper-produced content and `HtmlContentBuilder.AppendHtml(...)`, which Razor writes through its own `WriteTo` without encoding, so its producer must establish its safety, Blazor `MarkupString` values, other values that render their own markup, user-controlled URLs in `href`, `src` or `action`, where encoding does not stop a `javascript:` URL, attributes whose decoded value is parsed as HTML, such as `srcdoc`, unquoted attribute values, and values written into `<script>` blocks or event-handler attributes, where HTML encoding is not JavaScript encoding (use `JavaScriptEncoder` or JSON serialization there).
- **EF Core parameterizes queries**: LINQ queries and the interpolated methods `FromSqlInterpolated` (EF Core 3.0+), `ExecuteSqlInterpolated` and `FromSql` (EF Core 7.0+, whose only overload takes a `FormattableString`) turn values into parameters. Do not report SQL injection for them. **Exception:** `FromSqlRaw`, `ExecuteSqlRaw` and `SqlQueryRaw` with SQL built by concatenation or string interpolation, and `FromSql` or `ExecuteSqlCommand` on EF Core before 3.0 (check the `Microsoft.EntityFrameworkCore` version), where both also accept a plain string and send it as raw SQL, so `FromSql("SELECT … " + id)` or an interpolated string stored in a variable and passed to either is injectable.
