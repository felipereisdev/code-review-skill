# Clean Architecture — Code Review Checklist

Clean Architecture organizes code into concentric layers with a strict **Dependency Rule**: source code dependencies may only point inward. Outer layers know about inner layers; inner layers know nothing about outer layers.

| Layer (outer → inner) | What lives here |
|---|---|
| Frameworks & Drivers | HTTP framework, ORM, queues, 3rd-party SDKs, CLI |
| Interface Adapters | Controllers, Presenters, Repository implementations, Gateways |
| Use Cases / Interactors | Application-specific business rules, orchestration |
| Entities | Enterprise-wide business rules, pure domain objects |

## Dependency Rule
- **Inward-only imports**: no inner layer (`Entity`, `UseCase`) imports anything from an outer layer (`Controller`, `Eloquent`, `Request`, HTTP clients)
- **No framework in entities**: entity classes have zero imports from the application framework (`Illuminate\`, Spring annotations, etc.)
- **No framework in use cases**: use cases do not import controllers, HTTP request objects, or ORM models directly; they receive and return plain DTOs
- **Repository interfaces in the domain**: `UserRepositoryInterface` defined in the use-case/domain layer; Eloquent/DB implementation lives in the infrastructure layer

## Use Cases / Interactors
- **Single purpose**: each use case has one clearly named responsibility (e.g. `CreateOrderUseCase`, `CancelSubscriptionUseCase`), not a generic service with many methods
- **DTOs at boundaries**: data crossing layer boundaries uses plain data transfer objects, not HTTP request objects or ORM models
- **No side effects in entities**: entities enforce invariants and contain business rules; they do not send emails, dispatch events, or call external APIs directly
- **Delegation via interfaces**: use cases delegate I/O (database, email, external APIs) entirely through injected interfaces, never through concrete implementations

## Testability
- **Framework-free unit tests**: business rules (use cases and entities) testable without booting the framework, connecting to a database, or mocking HTTP
- **Stub/fake injection**: use cases tested by injecting in-memory fakes or stubs of their repository/gateway interfaces
- **No untestable god classes**: no single class accumulates so many responsibilities that it cannot be meaningfully unit tested in isolation

## Structure
- **Screaming Architecture**: top-level folder structure reveals the domain (e.g. `Orders/`, `Billing/`, `Identity/`), not the framework mechanics (`Controllers/`, `Models/` at the root)
- **Layer separation enforced**: each layer lives in a clearly named namespace or directory; framework code does not bleed into domain directories
