# Domain-Driven Design (DDD) — Code Review Checklist

> Apply this file only to code that has adopted DDD's building blocks, as the repository shows it: aggregate roots whose methods enforce invariants, value objects, repositories that load and save whole aggregates, bounded contexts with their own models and a translation between them, or an architecture document that names them. Folder names such as `domain/` alone do not prove it. Adopting DDD, or any one of its building blocks, is never a requirement, and code that does not use it is never a finding from this file. Check sibling code for the established conventions (see Consistency Check step), and report an item only with a concrete trigger → effect in the changed code.

## Aggregates and Invariants

- **Invariants bypassed outside the aggregate root**: a change that writes an aggregate's state without its root's methods, such as appending to `order.lines`, setting `order.status`, a bulk `UPDATE`, a queryset `update()` or raw SQL, skips the checks that those methods enforce and the events they record: a submitted order gets a new line, a total stops matching its lines, a state moves to one that it may not reach from where it is. **Not a finding:** a write that goes through the root's method, or a project whose model keeps its rules in domain services by design, as long as the change does not bypass that service.
- **Lost updates to an aggregate**: when the project protects aggregates with optimistic concurrency (a version column, an expected stream version), report a changed write only when it bypasses the check and can overwrite a concurrent change: an unconditional update keyed only by id, a stale copy given the current version without reloading its state, or a retry that suppresses the conflict and writes the same stale state with a fresh or ignored version. **Not a finding:** a save of stale state that the version check rejects, or a store or runtime that serializes every write to one aggregate, such as a single consumer per aggregate key.
- **Rules that span aggregates without the consistency they need**: a rule that involves two aggregates, such as reserving stock when an order is confirmed, needs either one transaction over both, where the store supports it, or a process that retries or compensates until both agree. A change that commits one aggregate and then changes the other in a second step, with nothing that retries or reconciles that step, leaves them disagreeing when it fails. **Not a finding:** one transaction that covers both: "modify one aggregate per transaction" is a design guideline, not a defect by itself.

**Bad** — the line goes straight into `order.lines`, so `Order.add_line`, which rejects changes once the order is submitted and keeps `total` in step with the lines, never runs:

```python
def add_gift_line(order_id, sku, orders):
    order = orders.get(order_id)
    order.lines.append(OrderLine(sku=sku, quantity=1, unit_price=Money.zero("EUR")))
    orders.save(order)
```

**Good** — the root method applies the invariants:

```python
def add_gift_line(order_id, sku, orders):
    order = orders.get(order_id)
    order.add_line(sku=sku, quantity=1, unit_price=Money.zero("EUR"))
    orders.save(order)
```

## Value Objects

- **Shared value objects changed in place**: the code shares values freely, such as a price read from a catalog cache, so a value object must not change after it is created. A change that adds a setter or an in-place operation to a type that the project treats as a value object changes every holder of the same instance: discounting one cart line changes the cached catalog price. **Not a finding:** a mutable type that the project never shares, such as a builder used inside one function.
- **Equality and validation that callers rely on**: callers compare a value object by value and trust that it is valid. A change that makes equality compare identity (a Python `@dataclass(eq=False)`, a Java class without `equals` and `hashCode`), or removes a check from its constructor (a negative amount, an email that is not normalized, an amount without a currency), breaks set membership, deduplication or a rule that relied on the check. An operation that mixes values the type keeps apart, such as adding amounts in two currencies without a conversion, gives a wrong result. **Not a finding:** a check that moved to a factory that every caller still goes through.

**Bad** — `add` changes the instance it is called on, so `price.add(shipping)` also changes the cached catalog price that `price` came from, and it adds amounts in different currencies:

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Money:
    amount: Decimal
    currency: str

    def add(self, other):
        self.amount += other.amount
        return self
```

**Good** — the value is frozen, `add` returns a new value, and mixed currencies raise an error:

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def add(self, other):
        if other.currency != self.currency:
            raise ValueError(f"cannot add {other.currency} to {self.currency}")
        return Money(self.amount + other.amount, self.currency)
```

## Bounded Contexts

- **Another context's model used directly**: when the project separates bounded contexts, a change that reads or writes another context's internal tables or classes bypasses that context's rules and breaks when it changes its model. A write that skips the owning context's checks is a **Warning** or worse under Severity Levels. Use the interface that the owning context publishes (an API, a published event, a module facade). **Not a finding:** a shared kernel that the project declares, or read-only use of a model that the owning context publishes for others.
- **Translation skipped at a boundary**: where the project maps data from another context or an external system through a translation layer (an anti-corruption layer), a change that uses the foreign value directly takes on the foreign meaning: a supplier's price in cents used where the context expects units, or the supplier's status names used where the context's own states drive the rules. **Not a finding:** a value whose meaning the two sides share by a documented contract.

## Domain Events

- **Events handled before the change commits**: when domain events trigger side effects, such as an email, a message to another service or a write elsewhere, a handler that runs before the aggregate's transaction commits acts on a change that may still roll back. Dispatch after commit, through an outbox or the framework's after-commit hook. Dispatch after commit in the same process can still lose the event when the process stops between the commit and the handler; an outbox keeps it and delivers it at least once, so its handler must tolerate a repeat. **Not a finding:** a handler that only changes state in the same transaction, which rolls back with it.

## Conventions, not defects

- Repositories per aggregate, factories, domain services, rich or anemic models, value objects for every concept, a domain event for every change, small aggregates, one aggregate per transaction and names from the ubiquitous language are design choices; their absence is not a finding. A name that says something different from what the code does is a naming finding of the Architecture category, not a DDD rule.

## Sources

- Aggregates, entities, value objects, repositories, domain events and bounded contexts: Eric Evans, "Domain-Driven Design Reference", https://www.domainlanguage.com/ddd/reference/
- Aggregate design and consistency between aggregates: Vaughn Vernon, "Effective Aggregate Design", https://www.dddcommunity.org/library/vernon_2011/
- Martin Fowler: "DDD_Aggregate", https://martinfowler.com/bliki/DDD_Aggregate.html; "ValueObject", https://martinfowler.com/bliki/ValueObject.html; "BoundedContext", https://martinfowler.com/bliki/BoundedContext.html
- Domain events and when to dispatch them: Microsoft, ".NET Microservices: Architecture for Containerized .NET Applications", "Domain events: Design and implementation", https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/domain-events-design-implementation
- Frozen dataclasses: Python `dataclasses` documentation, https://docs.python.org/3/library/dataclasses.html
- Transaction-bound event listeners: Spring Framework reference, https://docs.spring.io/spring-framework/reference/data-access/transaction/event.html

## Precedents

- **Writes through the root method**: a root method that checks an invariant enforces it for every caller that goes through it. Do not report a missing invariant check in a caller that changes the aggregate only through the root's methods. **Exception:** the change also writes the same state another way (direct access to a child collection, a bulk update, raw SQL, a reflective or ORM-level setter), or the root's check trusts a value that the caller passes without validation.
- **Immutable value types**: the fields of a Python `@dataclass(frozen=True)`, a Java `record` or a Kotlin `data class` with only `val` properties cannot be reassigned. Do not report aliasing of such an instance as shared mutation. **Exception:** a field holds a mutable object that callers change (a list, a dict, a `java.util.Date`), or the code bypasses the immutability, as `object.__setattr__` or reflection does.
- **After-commit event listeners**: a Spring `@TransactionalEventListener` in its default `AFTER_COMMIT` phase runs only after the publishing transaction commits, so it never sees a rolled-back change. Do not report a domain event published inside the transaction when its handlers are such listeners. **Exception:** a handler that runs earlier (a plain `@EventListener`, `phase = TransactionPhase.BEFORE_COMMIT`), an event published without an active transaction, which such a listener ignores unless it sets `fallbackExecution = true`, or a handler whose own failure is lost because nothing retries it after commit.
