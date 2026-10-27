# CQRS (Command Query Responsibility Segregation) — Code Review Checklist

> Apply this file only to code that separates the model that changes state (commands and their handlers) from the model that answers queries (query handlers, read models or projections), as the repository shows it: command and query handler types, a command or query bus the project uses (such as MediatR, Axon or the NestJS CQRS module), projection code that updates read tables or documents, or an architecture document. CQRS does not require event sourcing, separate databases, a message bus or eventual consistency: read the code for which of these the project actually uses before applying an item that depends on one. Adopting CQRS is never a requirement, and code that does not use it is never a finding from this file. Check sibling handlers for the established conventions (see Consistency Check step), and report an item only with a concrete trigger → effect in the changed code.

## Commands

- **Invariants checked against the read model**: a command handler that validates a rule, such as a unique email, a credit limit or the available stock, by querying a read model that is updated after the write lets two concurrent commands, or a command that arrives before the projection catches up, both pass and break the rule. Check the rule on the write side, against state that the write transaction locks, versions or constrains. **Not a finding:** a read model updated in the same transaction as the write and read inside it under a lock or a constraint, or a read-model check that only gives early feedback while the write side still enforces the rule.
- **Lost updates on the write side**: a handler that loads state, changes it and saves it without the concurrency check that the project uses (an expected version, a row version, an `ETag`, a conditional update) overwrites a concurrent change to the same state. **Not a finding:** one writer per key by construction, such as a consumer that handles the commands of one aggregate one at a time.
- **What a command returns**: a command may return an acknowledgement, the new identifier, a version or validation errors; CQRS does not forbid it. It is a finding only when the caller's use of the result fails: the project's bus or asynchronous endpoint discards the result or answers before the command runs (for example with `202 Accepted`) and the change reads it anyway, or the handler returns data read from a read model that is updated after commit, so the caller sees the state from before its own command. **Not a finding:** a returned identifier or version, or data taken from the write model that the handler just saved.
- **Queries that change state**: a query handler that writes, such as marking messages as read, creating a missing record or consuming a one-time token, changes state again each time something repeats the query: a retry, a cache refresh, a prefetch or a monitoring probe. On a read replica the write fails. **Not a finding:** logging, metrics, tracing and cache fills that no business rule reads.

**Bad** — the email is checked against the read model, which the projection updates after the commit, so two registrations with the same email a moment apart both succeed:

```python
def handle_register_user(command, users_read_model, user_store):
    if users_read_model.find_by_email(command.email) is not None:
        raise EmailTaken(command.email)
    user_store.add(User.register(command.user_id, command.email))
```

**Good** — the users table of the write store has a unique index on the normalized email, so the database rejects the second registration, and the handler turns the violation into the domain error:

```python
def handle_register_user(command, user_store):
    try:
        user_store.add(User.register(command.user_id, command.email.strip().lower()))
    except DuplicateKeyError:
        raise EmailTaken(command.email) from None
```

## Projections and Read Models

- **Projections that apply an event twice**: projections fed by an at-least-once transport, or rebuilt by a replay, see some events again after a crash, a timeout or a rebalance. An increment such as `balance = balance + amount` applied twice gives a wrong value. Record the last processed position or event ID in the same transaction as the read-model update and skip what was already applied, or write values that a repeat cannot change. **Not a finding:** an upsert that sets values from the event when the events of one key arrive in order (see the order item below).
- **Position and read model saved separately**: a projection that saves its checkpoint and its read-model update in two transactions applies an event again after a crash between them when it saves the checkpoint last, and skips the event for good when it saves the checkpoint first. **Not a finding:** a read model and a checkpoint in different stores when every update is idempotent and the checkpoint is saved after the update.
- **Order assumed across streams or partitions**: a projection that combines events from several aggregates, streams or partitions cannot assume the order in which they were written. An `OrderShipped` that arrives before the `OrderPlaced` row exists updates nothing, and an older state that arrives late overwrites a newer one when the handler sets values without comparing a version or sequence number. Check the ordering guarantee of the store or transport: usually one stream, partition or key. **Not a finding:** events of a single stream or key, delivered in order and handled one at a time.
- **A write-side change that the projection does not follow**: a change that adds an event type, adds or renames a field, or changes what a field means, without updating each projection that builds a read model from it, leaves the read model wrong without any error. A change to how a projection computes a value applies only to the events processed after deployment unless the read model is rebuilt or backfilled. **Not a finding:** a field that no projection reads, or a change shipped with a rebuild or a backfill.

**Bad** — a redelivered `DepositRecorded` adds the amount twice:

```python
def on_deposit_recorded(event, db):
    with db.transaction():
        db.execute(
            "UPDATE account_balances SET balance = balance + %s WHERE account_id = %s",
            (event.amount, event.account_id),
        )
```

**Good** — `processed_events` has a primary key on `(projection, event_id)`, and the event ID is recorded in the same transaction as the update, so a redelivery changes nothing (in PostgreSQL, `ON CONFLICT DO NOTHING RETURNING` returns no row when the insert is skipped):

```python
def on_deposit_recorded(event, db):
    with db.transaction():
        first_time = db.execute(
            "INSERT INTO processed_events (projection, event_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING RETURNING event_id",
            ("account_balances", event.id),
        ).fetchone()
        if first_time:
            db.execute(
                "UPDATE account_balances SET balance = balance + %s WHERE account_id = %s",
                (event.amount, event.account_id),
            )
```

## Conventions, not defects

- Event sourcing, separate read and write databases, a command or query bus, one handler per command, commands that return nothing, imperative command names and past-tense event names are design choices; their absence is not a finding.
- An eventually consistent read model is a decision, not a defect: a finding needs a caller or a rule that the change makes depend on reading its own write.

## Sources

- CQRS and when it fits: Martin Fowler, "CQRS", https://martinfowler.com/bliki/CQRS.html
- Command-query separation and its exceptions: Martin Fowler, "CommandQuerySeparation", https://martinfowler.com/bliki/CommandQuerySeparation.html
- Commands, read models and eventual consistency: Greg Young, "CQRS Documents", https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf
- CQRS and the consistency of read models: Microsoft Azure Architecture Center, "CQRS pattern", https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs
- Event sourcing, projections and replays: Microsoft Azure Architecture Center, "Event Sourcing pattern", https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing
- `INSERT ... ON CONFLICT DO NOTHING` and `RETURNING`: PostgreSQL documentation, https://www.postgresql.org/docs/current/sql-insert.html

## Precedents

- **Projections updated in the write transaction**: when the project updates a read model in the same database transaction as the write, a query that runs on the same database after the command commits sees the write. Do not report stale reads or a lost projection update for such a read model. **Exception:** the update runs after commit (an after-commit hook, a message, a background job), writes to another database or connection, or the query reads from a replica with replication lag.
- **Commands that return an identifier or a result**: returning the new identifier, a version, an acknowledgement or validation errors from a command handler is a common CQRS design. Do not report a value returned by a command as a CQRS violation. **Exception:** the project's command contract (its bus, a base class or an asynchronous endpoint) discards or never delivers the result and the caller depends on it, or the returned data comes from a read model that is updated after commit.
- **Unique constraints on the write store**: a unique index or key in the write store rejects the second of two concurrent commands for the same value. Do not report a check-then-insert race when such a constraint covers the rule. **Exception:** the constraint does not match the rule (another normalization such as letter case, another scope such as a tenant, soft-deleted rows that the rule ignores but the index counts), or the constraint exists only in the read model.
