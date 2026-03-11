# Go — Code Review Checklist

- **Error wrapping**: errors wrapped with `fmt.Errorf("...: %w", err)` to preserve context; not discarded
- **Goroutine leaks**: goroutines have a clear exit path; channels are closed; `context` cancellation propagated
- **Context propagation**: `context.Context` passed as first argument through call chains; not stored in structs
- **Defer usage**: `defer` used for cleanup (close, unlock); not used in loops where it would delay execution
- **Interface design**: interfaces defined at the consumer, not the producer; small, focused interfaces preferred
- **Error types**: sentinel errors or typed errors used for programmatic handling; plain strings for log-only errors
