# Observability

Report what the change breaks or hides, never a missing observability practice (see **Missing mechanism or pattern** under Do Not Report in SKILL.md).

- **Debug output left behind**: `console.log`, `var_dump`, `print` or similar debug output that the change leaves in production code, where the project uses a logger
- **Sensitive data in logs**: passwords, tokens, PII or secrets that the change logs, even partially
- **Wrong log levels**: an error or a critical event that the change logs at `debug`, so it never shows in production
- **Swallowed errors**: an exception that the change catches and neither handles, rethrows nor reports, where the project reports such errors (for example to Sentry or Bugsnag)
- **Broken correlation**: the change drops a trace or correlation ID that the project already propagates through that flow
