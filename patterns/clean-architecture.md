# Clean Architecture — Code Review Checklist

> Apply this file only to code that has adopted Clean Architecture or a close variant (hexagonal, ports and adapters, onion), as the repository shows it: an architecture document or decision record, an import rule that a check enforces (an ArchUnit test, an import-linter contract, a dependency-cruiser or Deptrac rule, separate modules whose build files forbid the dependency), or a layer split that sibling code follows consistently. A folder named `domain/` or a class named `*UseCase` alone does not prove it. Adopting this architecture is never a requirement, and code that does not use it is never a finding from this file. Map each item to the layers the project itself defines, check sibling code for the established variant (see Consistency Check step), and report an item only with a concrete trigger → effect in the changed code. A dependency that points the wrong way but changes no behavior is a **Suggestion**; it is a **Warning** or **Critical** only through a wrong result, lost data or a security hole, as Severity Levels says.

| Layer (outer → inner) | Typical contents |
|---|---|
| Frameworks & Drivers | HTTP framework, ORM, queues, third-party SDKs, CLI |
| Interface Adapters | Controllers, presenters, repository implementations, gateways |
| Use Cases | Application rules and the orchestration of one operation |
| Entities | Business rules that hold for every application |

Source code dependencies point inward: an inner layer names nothing from an outer one, and an outer layer reaches the inner rules only through the use cases and the ports (interfaces) that the inner layers own.

## Dependency Rule

- **Inner code that imports outer code**: a change makes an entity or a use case import a controller, an ORM model, an HTTP request object or a framework service, where the project's rule forbids it. Report it when it has an effect beyond the rule itself: the inner code now behaves differently outside a web request (a job, a CLI command or a test calls the use case, and the framework object it reads is missing or holds another request's data), an import cycle breaks module loading, or a business rule now depends on a framework default. Without such an effect it is a **Suggestion**. **Not a finding:** an import that the project's own rule allows, such as the standard library, a shared kernel or a utility library the inner layers may use, or a project that consistently uses its framework's models as entities, as many Django and Rails projects do.
- **A path that skips the use case**: a new controller, job, event handler or admin action writes through a repository, the ORM or raw SQL when the existing use case for that operation enforces a rule on the way: an authorization or ownership check, a state transition, an invariant, an audit record or a domain event. The new path stores a state the rule forbids, or a side effect that the use case performs never happens. A missing authorization check reached this way is **Critical** under Severity Levels. **Not a finding:** a write to which the use case adds no rule, or a path that calls the same domain method that holds the rule.
- **An adapter chosen inside the use case**: a use case or an entity constructs or looks up a concrete adapter (a mail client, a payment gateway, an HTTP client) instead of using the port that the composition root wires. The choice that the composition root makes, such as the sandbox gateway in staging, the fake in tests or the retrying client in production, is bypassed, so the code talks to the wrong system or loses the behavior that the wired adapter adds. **Not a finding:** a pure function with no I/O, such as a price calculation or a value parser.
- **Framework or ORM objects crossing the use-case boundary**: where the project passes plain data across the boundary, a change that returns an ORM entity or accepts a framework request object can fail at runtime or leak data. A lazy relation read after the session closes raises an error (SQLAlchemy's `DetachedInstanceError`, Hibernate's `LazyInitializationException`), and a presenter that serializes the whole entity exposes columns that the response did not include before, such as a password hash. **Not a finding:** a project that consistently passes ORM objects across layers, with eager loading or a session that stays open for the whole request.

**Bad** — the new endpoint cancels the order through the repository, so `CancelOrder`, which checks the owner, rejects shipped orders and refunds the payment, never runs: any signed-in user can cancel any order, shipped orders included, and nothing is refunded:

```python
@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, user=Depends(current_user), orders=Depends(get_order_repository)):
    order = orders.get(order_id)
    order.status = "cancelled"
    orders.save(order)
    return {"status": order.status}
```

**Good** — the endpoint delegates to the use case that already holds those rules:

```python
@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, user=Depends(current_user), cancel=Depends(get_cancel_order)):
    result = cancel.execute(order_id=order_id, requested_by=user.id)
    return {"status": result.status}
```

## Use Cases and Ports

- **A port whose contract changes under its adapters**: a change alters what a port promises, such as returning `None` instead of raising when a record is missing, accepting an amount without a currency or changing a unit, while an adapter or a caller still follows the old contract. In a language without static types, or with an adapter registered by name, nothing fails at build time, and the use case acts on a wrong value at runtime. Check every adapter and fake of the port, including the ones in tests. **Not a finding:** an additive change, such as a new optional parameter whose default keeps the old behavior.
- **A transaction boundary that moves**: where the use case owns the unit of work and its writes commit together, a change that commits inside a repository adapter, or splits the use case's writes across two commits, leaves a partial change when a later step fails: an order saved without its stock reservation, an account debited without the matching credit. **Not a finding:** a project whose adapters commit each write by design and whose use cases either compensate for a failed later step, run under a recovery process that retries the operation to completion or reconciles the partial work after a crash, or accept a partial state as a deliberate, documented contract. Idempotence of a repeated call alone is not a recovery process: when nothing retries or reconciles the unfinished work, a crash after the first commit leaves the partial change in place.
- **Side effects inside entities**: an entity method that sends an email, publishes a message or calls an external API performs that effect even when the use case's transaction later rolls back, and performs it again when the use case is retried. Record the intent (a domain event or a returned value) and let the use case act on it after commit. **Not a finding:** an entity that only records an event for the use case to dispatch.

**Bad** — the repository commits on every `save`, so a failure after the first `save` leaves both balances changed without the ledger entry:

```python
class SqlAccountRepository:
    def __init__(self, session):
        self.session = session

    def save(self, account):
        self.session.add(account)
        self.session.commit()


class TransferFunds:
    def __init__(self, accounts, ledger):
        self.accounts = accounts
        self.ledger = ledger

    def execute(self, source_id, target_id, amount):
        source = self.accounts.get(source_id)
        target = self.accounts.get(target_id)
        source.withdraw(amount)
        target.deposit(amount)
        self.accounts.save(source)
        self.accounts.save(target)
        self.ledger.append(source_id, target_id, amount)
```

**Good** — the use case runs every write in one unit of work, and the repository only adds to it; this holds because the ledger is a table in the same database, as `uow.ledger` shows. A ledger in another system needs an outbox or a compensation instead:

```python
class SqlAccountRepository:
    def __init__(self, session):
        self.session = session

    def save(self, account):
        self.session.add(account)


class TransferFunds:
    def __init__(self, unit_of_work):
        self.unit_of_work = unit_of_work

    def execute(self, source_id, target_id, amount):
        with self.unit_of_work as uow:
            source = uow.accounts.get(source_id)
            target = uow.accounts.get(target_id)
            source.withdraw(amount)
            target.deposit(amount)
            uow.accounts.save(source)
            uow.accounts.save(target)
            uow.ledger.append(source_id, target_id, amount)
            uow.commit()
```

## Conventions, not defects

- The number and names of the layers, the folder layout (by feature or by layer), one class per use case or a service with several methods, an interface for every dependency, DTOs at every boundary, framework-free entities and unit tests that never boot the framework are design choices. Code that does not follow them, or follows the project's own variant consistently, is not a finding; a change that departs from the variant the project already uses is a **Suggestion** at most (see Consistency Check step).
- A use case or an entity that collects many responsibilities is a structure concern of the Architecture category, reported only for code the change adds.

## Sources

- The Dependency Rule and the layers: Robert C. Martin, "The Clean Architecture", https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Ports and adapters: Alistair Cockburn, "Hexagonal Architecture", https://alistair.cockburn.us/hexagonal-architecture/
- Unit of Work: Martin Fowler, Catalog of Patterns of Enterprise Application Architecture, https://martinfowler.com/eaaCatalog/unitOfWork.html
- Composition root and dependency injection: Martin Fowler, "Inversion of Control Containers and the Dependency Injection pattern", https://martinfowler.com/articles/injection.html
- Import rules enforced by a check: ArchUnit user guide, https://www.archunit.org/userguide/html/000_Index.html; import-linter contract types, https://import-linter.readthedocs.io/en/stable/contract_types/
- Detached instances and lazy loading: SQLAlchemy session state management, https://docs.sqlalchemy.org/en/20/orm/session_state_management.html; Hibernate ORM user guide, https://docs.jboss.org/hibernate/orm/6.6/userguide/html_single/Hibernate_User_Guide.html

## Precedents

- **An import rule that a check already enforces**: when the repository runs an architecture test or an import linter on every change (an ArchUnit test, an import-linter contract, a dependency-cruiser or Deptrac rule) and its rule covers the changed module, that check already fails on a forbidden import. Do not report an import that such a rule forbids. **Exception:** the rule does not cover the changed module or the import (a new package outside its configured layers, an ignore entry or a suppression that the change adds, a dynamic import or a reflective lookup that the tool cannot see), or the check does not run on this change.
- **Composition roots and tests may know every layer**: the entry point that wires the application (the main module, the dependency-injection configuration, the framework bootstrap) and the test fixtures construct concrete adapters and pass them inward by design. Do not report concrete adapters imported or constructed there. **Exception:** a use case or an entity itself constructs or looks up the concrete adapter, so the wiring that the composition root chose is bypassed.
- **Reads served outside the use-case layer**: many projects serve read-only requests from a query object or a read model without a use case, and sibling reads show whether this project does. Do not report a read endpoint that skips the use-case layer the way sibling reads do. **Exception:** the use case for the same data applies a rule that the direct query omits, such as an ownership or tenant filter, a soft-delete filter or the redaction of a field.
