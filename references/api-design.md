# API Design *(only if the diff includes API endpoints or API client code)*

- **HTTP methods**: correct verbs used (`GET` for reads, `POST` for creation, `PUT`/`PATCH` for updates, `DELETE` for removal)
- **Status codes**: correct HTTP status codes returned (`201` for creation, `204` for no content, `422` for validation errors, `404` for not found, etc.)
- **Breaking changes**: the change breaks the contract of an existing public endpoint (a removed or renamed field, a changed type or status code) without the versioning or deprecation practice the project already uses
- **Consistent error responses**: error payloads follow a uniform structure across all endpoints
- **Unbounded lists**: a list endpoint that the change adds returns a collection that grows with data, without the pagination the project already uses
- **Filtering & sorting**: query parameters follow established conventions
- **Idempotency**: a `PUT`, `PATCH` or `DELETE` that the change adds has a different effect when it runs twice; never ask for idempotency keys on a `POST` the project does not already protect that way
- **No sensitive data in URLs**: tokens, passwords, and PII passed in headers or body, not in query strings or paths
- **GraphQL** *(only if project uses GraphQL)*: N+1 prevented with DataLoader, query depth limited, introspection disabled in production, mutations validate input
