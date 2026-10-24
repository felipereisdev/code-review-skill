# API Design *(only if the diff includes API endpoints or API client code)*

- **HTTP methods**: correct verbs used (`GET` for reads, `POST` for creation, `PUT`/`PATCH` for updates, `DELETE` for removal)
- **Status codes**: correct HTTP status codes returned (`201` for creation, `204` for no content, `422` for validation errors, `404` for not found, etc.)
- **Versioning**: API version is reflected in the URL or header; breaking changes bump the version
- **Consistent error responses**: error payloads follow a uniform structure across all endpoints
- **Pagination**: consistent strategy used (cursor or offset); metadata included in response
- **Filtering & sorting**: query parameters follow established conventions
- **Idempotency**: `PUT`/`PATCH`/`DELETE` operations are idempotent; `POST` operations are idempotent where appropriate (e.g. with idempotency keys)
- **No sensitive data in URLs**: tokens, passwords, and PII passed in headers or body, not in query strings or paths
- **GraphQL** *(only if project uses GraphQL)*: N+1 prevented with DataLoader, query depth limited, introspection disabled in production, mutations validate input
