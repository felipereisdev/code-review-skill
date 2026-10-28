# Microservices — Code Review Checklist

> Apply this file to changes that cross a network boundary between separately deployed services: an HTTP or gRPC client or server, a published API or message contract, or data that one service owns and another uses. The repository shows the services: separate deployables with their own manifests, images or charts, service clients, and API definitions such as OpenAPI files or `.proto` files. Splitting a system into services is never a requirement, and a modular monolith or a database shared on purpose is never a finding from this file. Timeouts, retries, backoff and circuit breakers for each call follow the Resilience category; this file covers what changes because the other side is deployed, scaled and fails on its own. Check sibling services and clients for the established conventions (see Consistency Check step), and report an item only with a concrete trigger → effect in the changed code.

## Data Ownership and Consistency

- **Another service's data written directly**: where the project gives each service its own tables, schema or database, a change that reads or writes another service's tables bypasses that service's validation, events and caches, and breaks when the owner changes its schema. A write that skips the owner's checks is a **Warning** or worse under Severity Levels. **Not a finding:** a database that the project shares on purpose and consistently, or a read-only replica or reporting view that the owner publishes.
- **Atomicity assumed across services**: no local transaction covers another service: a database transaction (for example Spring's `@Transactional`) around a remote call does not roll the remote side back. A change that calls two services in sequence, or writes locally and then calls a service, leaves a partial result when a later step fails, unless something compensates, retries or reconciles it, such as a saga with compensating actions. A timeout does not mean that the remote call failed: it may have succeeded. **Not a finding:** later steps that a durable process retries until they succeed and that are idempotent, or a partial state that the business accepts and that a reconciliation job already corrects.
- **Retries of calls that are not idempotent**: retrying a `POST` or another non-idempotent call after a timeout or a dropped connection repeats it when the first attempt succeeded: a second payment, a duplicate order. Send an idempotency key that stays the same across retries, when the callee honors one, or retry only idempotent calls. **Not a finding:** a callee that deduplicates by a key that the caller keeps across retries (see Precedents).

**Bad** — the card is charged before the stock is reserved, so `OutOfStock` leaves a paid cart with nothing reserved and nothing refunded:

```python
def checkout(cart, payments, inventory):
    charge = payments.charge(cart.customer_id, cart.total, idempotency_key=cart.id)
    inventory.reserve(cart.items, reservation_id=cart.id)
    return charge.id
```

**Good** — the step that can be undone runs first. A declined payment releases the reservation; an error with an unknown outcome, such as a timeout, keeps it, because the charge may have gone through, and the order service's reconciliation settles it against the payment provider. A retry reuses `cart.id` as the idempotency key. Nothing here is atomic: a failed `confirm` also leaves a reservation that the same reconciliation settles:

```python
def checkout(cart, payments, inventory):
    reservation = inventory.reserve(cart.items, reservation_id=cart.id)
    try:
        charge = payments.charge(cart.customer_id, cart.total, idempotency_key=cart.id)
    except PaymentDeclined:
        inventory.release(reservation.id)
        raise
    inventory.confirm(reservation.id)
    return charge.id
```

## Contracts Between Services

- **Breaking changes to an API that other services call**: services deploy separately, so old and new versions of a caller and a callee run together during a rollout and after a rollback. Removing or renaming a field, changing a type, a unit, a status code or an error format, adding a required request field, or adding an enum value that a caller maps exhaustively breaks the callers that still use the old contract. In Protocol Buffers, reusing or renumbering a field number, or changing a field to an incompatible type, makes old and new binaries read each other's data wrongly, often without an error. **Not a finding:** an additive change that existing callers ignore (see Precedents), or a change whose incompatible interactions are excluded in both directions. Old callers, consumers and stored records must not read the new format, and new callers, consumers and stored records must not read the old format from an old callee, from a queued message or from retained data. An effective compatibility mechanism meets that for every producer-consumer pair that stays active during the rollout, such as a callee that sends both the old and the new field and is fully deployed before any caller reads the new one, with new callers that fall back to the old field when the new one is missing and new readers that accept retained records in the old format. A complete cutover meets it too when it stops all old-version traffic and drains or converts the incompatible messages and records before the new version serves them. Sharing a chart, pipeline or release unit does not by itself prevent old and new replicas from running together, and a callee that sends both fields protects only the callers that reach the new replica.
- **A deployment order required but not handled**: a change that works only when one service deploys before another, such as a caller that sends a field the callee does not accept yet, fails during the rollout unless it is split into compatible steps or guarded by a flag. **Not a finding:** a change that works in either order.

**Bad** — `string currency = 2` was removed and its number reused for `region`, so a client built from the old definition reads the region code as the currency, without any error:

```protobuf
syntax = "proto3";

message Invoice {
  string id = 1;
  string region = 2;
  int64 amount_cents = 3;
}
```

**Good** — the old number and name are reserved, and the new field takes an unused number:

```protobuf
syntax = "proto3";

message Invoice {
  reserved 2;
  reserved "currency";
  string id = 1;
  int64 amount_cents = 3;
  string region = 4;
}
```

## Calls Between Services

- **Identity trusted from a header that anyone can send**: a service that takes the caller's identity or permissions from a header such as `X-User-Id`, on the assumption that a gateway sets it, lets any client that reaches the service another way, or whose header the gateway passes through, act as any user. That is a **Critical** security hole under Severity Levels. Verify a signed token (signature, issuer, audience, expiry), or show that only the gateway reaches the service and that it replaces the header. **Not a finding:** the gateway-only case that the Precedents describe.
- **Calls per item in a request path**: a handler that calls another service once per item of a list makes each request's latency and the callee's load grow with the data, and one slow call delays the whole response: a **Warning** under the hot-path rule of Severity Levels. Use a batch endpoint or bounded concurrent calls. **Not a finding:** a list with a small fixed bound, or calls made outside the request path.
- **Retries at every layer**: when each service in a chain retries its calls, one failure at the bottom multiplies: three layers that each make 3 attempts send up to 27 requests to the last service while it is already failing. Retry at one layer, or use a retry budget or a circuit breaker. **Not a finding:** retries with backoff at a single layer.

**Bad** — the service trusts `X-User-Id`, and the ingress in the same chart also routes public traffic to it, so a request with a forged header reads another user's invoice:

```js
app.get("/invoices/:id", async (req, res) => {
  const userId = req.get("X-User-Id");
  res.json(await invoices.findForUser(req.params.id, userId));
});
```

**Good** — `requireJwt`, the project's middleware, verifies the signature, issuer, audience and expiry of the token that the gateway forwards, and the user comes from the token's subject:

```js
app.get("/invoices/:id", requireJwt({ issuer: GATEWAY_ISSUER, audience: "invoices" }), async (req, res) => {
  res.json(await invoices.findForUser(req.params.id, req.auth.sub));
});
```

## Conventions, not defects

- A database per service, contract tests, distributed tracing, an API gateway, a service mesh, synchronous or asynchronous communication and the size of a service are design choices; their absence is not a finding. A change that drops trace propagation the project already has is a matter for the Observability category, not a defect of this pattern.

## Sources

- Microservices and decentralized data management: James Lewis and Martin Fowler, "Microservices", https://martinfowler.com/articles/microservices.html
- Database per service and sagas: Chris Richardson, microservices.io, https://microservices.io/patterns/data/database-per-service.html and https://microservices.io/patterns/data/saga.html
- Compatible changes: Protocol Buffers, "Updating A Message Type", https://protobuf.dev/programming-guides/proto3/#updating; Google API Improvement Proposals, "AIP-180: Backwards compatibility", https://google.aip.dev/180; ProtoJSON unknown-field handling, https://protobuf.dev/programming-guides/json/
- Retry amplification: Google SRE book, "Addressing Cascading Failures", https://sre.google/sre-book/addressing-cascading-failures/
- Identity between services: OWASP Microservices Security Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Microservices_Security_Cheat_Sheet.html
- Idempotency keys: Stripe API reference, "Idempotent requests", https://docs.stripe.com/api/idempotent_requests
- Strict JSON readers: Jackson `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES`, https://github.com/FasterXML/jackson-databind/blob/2.17/src/main/java/com/fasterxml/jackson/databind/DeserializationFeature.java

## Precedents

- **Additive, optional changes**: adding an optional field to a response or a message, or a new endpoint, does not break callers that skip fields they do not know: Protocol Buffers binary parsers keep or skip unknown fields, and most JSON clients ignore them. Do not report such an addition as a breaking change. **Exception:** a ProtoJSON parser (protobuf messages read as JSON), which rejects unknown fields by default unless configured to ignore them; a caller whose deserializer rejects unknown fields (a JSON Schema with `additionalProperties: false`, a Jackson 2 `ObjectMapper` with `FAIL_ON_UNKNOWN_PROPERTIES` enabled, as a plain mapper is by default), a new enum value that a caller maps exhaustively, or a field that the server now requires in requests.
- **Identity set by a gateway that alone reaches the service**: when the repository shows that only the gateway or the mesh can reach the service (a network policy, a private listener, mutual TLS with an authorization policy) and that the gateway removes any identity header sent by the client and sets it from a verified token, the service may read the identity from that header. Do not report header-based identity under those conditions. **Exception:** another route reaches the service (a public ingress, a load balancer, another internal caller that forwards client headers), or the change stops the gateway from removing the header.
- **Idempotency keys honored by the callee**: a callee that deduplicates requests by an idempotency key answers a repeated key with the first result. Do not report a retried remote call as a duplicate when the caller keeps the same key across retries and the callee honors it for that operation. **Exception:** the key is generated per attempt, the callee keeps keys for less time than the caller keeps retrying, or the retry changes the request's parameters, which some APIs reject and others treat as a new request.
