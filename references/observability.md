# Observability

- **Structured logging**: logs use a structured format (JSON or key=value); no `console.log` / `var_dump` left in production code
- **Sensitive data in logs**: no passwords, tokens, PII, or secrets logged — even partially
- **Log levels**: appropriate log levels used (`debug`, `info`, `warning`, `error`); no critical events logged at `debug`
- **Correlation IDs**: requests and async jobs carry a trace/correlation ID through logs
- **Error reporting**: exceptions are captured and forwarded to the error tracking system (e.g. Sentry, Bugsnag)
- **Metrics**: significant new operations (queue jobs, external calls, cache hits) are instrumented where relevant
