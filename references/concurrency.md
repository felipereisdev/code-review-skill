# Concurrency & Thread Safety *(only if the diff involves shared state, background jobs, or concurrent operations)*

- **Race conditions**: operations on shared state are atomic or properly synchronized
- **Locks & mutexes**: locking strategy is correct; no deadlock potential (consistent lock ordering)
- **Atomic operations**: counters and flags updated atomically (e.g. database atomic increments, compare-and-swap)
- **Job uniqueness**: a background job that the change adds, and that must not run twice at once, can run twice at once
- **Shared mutable state**: the change adds global or static mutable state that concurrent requests or jobs write
