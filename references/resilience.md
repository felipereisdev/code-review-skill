# Resilience & Fault Tolerance *(only if the diff involves external calls, queues, or critical flows)*

- **Timeouts**: all outbound HTTP calls, database queries, and queue operations have explicit timeouts
- **Retry with backoff**: transient failures retried with exponential backoff and jitter; non-retriable errors not retried
- **Circuit breakers**: repeated failures to an external dependency trip a circuit breaker to prevent cascade
- **Graceful degradation**: the system degrades gracefully when a non-critical dependency is unavailable
- **Idempotency**: operations that may be retried are idempotent (safe to execute more than once)
- **Bulkhead isolation**: slow or failing dependencies do not exhaust shared resources (thread pools, connections)
