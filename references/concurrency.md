# Concurrency & Thread Safety *(only if the diff involves shared state, background jobs, or concurrent operations)*

- **Race conditions**: operations on shared state are atomic or properly synchronized
- **Locks & mutexes**: locking strategy is correct; no deadlock potential (consistent lock ordering)
- **Atomic operations**: counters and flags updated atomically (e.g. database atomic increments, compare-and-swap)
- **Job uniqueness**: background jobs that must not run concurrently are protected by a unique lock
- **Shared mutable state**: global or static mutable state avoided; dependencies injected rather than shared
