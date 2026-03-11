# .NET / C# — Code Review Checklist

- **Async/await**: `async`/`await` used consistently; no `.Result` or `.Wait()` blocking calls on async methods
- **IDisposable**: disposable resources wrapped in `using` statements or properly disposed in `Dispose()` method
- **Nullable reference types**: nullable annotations used correctly; null checks present where needed
- **Dependency injection**: services registered with correct lifetime (`Transient`, `Scoped`, `Singleton`); no captive dependency issues
- **LINQ**: LINQ queries deferred correctly; `ToList()`/`ToArray()` called only when materialization is needed
- **Entity Framework**: no N+1 queries; `Include`/`ThenInclude` used for related data; migrations reviewed
