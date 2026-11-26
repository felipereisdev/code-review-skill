# Resilience & Fault Tolerance *(only if the diff involves external calls, queues, or critical flows)*

Report a failure the change causes, never a missing resilience pattern (see **Missing mechanism or pattern** under Do Not Report in SKILL.md).

- **Calls that can hang**: an outbound call on a request path or in a job that the change adds without a timeout, where the client's default waits without limit, so a slow dependency hangs requests or workers. Not a finding when the client, the framework or the project's shared client already sets a timeout.
- **Unsafe retries**: a retry that the change adds repeats an operation that is not safe to run twice (a charge, a sent message, a created record), or retries without a bound.
- **Half-done critical flows**: a failure of the external call leaves a critical flow half-done, such as a payment charged but not recorded, or a record saved but its event never sent, with no way to detect or recover it.
- **Retriable but not idempotent**: an operation that the change makes run again on failure, such as a queue consumer or a webhook handler, has an effect that duplicates when it runs twice.

Circuit breakers, bulkheads, backoff with jitter and graceful-degradation layers are architecture decisions, not defects of a change: never ask for them, unless the project already uses one for that dependency and the change bypasses it.
