# Domain-Driven Design (DDD) — Code Review Checklist

- **Domain logic placement**: business rules live in domain entities or services, not in controllers or repositories
- **Value objects**: domain concepts with no identity modeled as immutable value objects
- **Aggregate boundaries**: aggregates enforce invariants; external code does not bypass aggregate roots
- **Domain events**: significant domain state changes emit domain events for side-effect decoupling
