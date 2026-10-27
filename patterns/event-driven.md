# Event-Driven Architecture — Code Review Checklist

> Apply this file to code that publishes or consumes events or messages, through a broker or a queue, an event bus, webhooks, or an in-process dispatcher whose handlers have side effects, and to event-sourced code, whose events are the stored state. What a delivery guarantees comes from the transport, its configuration and the code, never from a name: "exactly once" in a product describes a narrow feature, such as Kafka transactions between Kafka topics, and never covers a database write or an external call by itself. A publish to a broker outside the database is not part of the database commit unless a distributed transaction, such as XA, covers both. Read the client, its configuration and the broker or queue settings that the repository manages before applying an item; the Kafka and RabbitMQ stack file covers client-specific rules when it is loaded. Using events is never a requirement, and code that does not use them is never a finding from this file. Check sibling producers and consumers for the established conventions (see Consistency Check step), and report an item only with a concrete trigger → effect in the changed code.

## Publishing

- **A state change and its event written separately**: committing a database change and publishing its event as two steps loses one of them when the process fails between them: a committed change whose event never goes out, or, when the code publishes first, an event for a change that then rolls back. Write the event to an outbox table in the same transaction and let a relay publish it, use change data capture, or make consumers reconcile from the source. An outbox relay publishes at least once, so consumers still see duplicates. **Not a finding:** an enqueue that commits atomically with the state change in the same database transaction, such as a queue or job table in that database; a broker send and the database change enlisted in the same distributed transaction, such as XA; or an event that consumers treat as a hint and recover from when it is missing, such as a cache invalidation backed by a short expiry.
- **Publish failures that nobody sees**: a publish whose result the code never checks, such as a send that is never awaited, a delivery callback that is never read, or an error that is logged and swallowed, reports success for an event that was never written. **Not a finding:** best-effort events that the design allows to lose, such as metrics.

**Bad** — a crash after the commit, or a broker error, loses the `orders.placed` event, and nothing downstream ever learns about the order:

```python
def place_order(order, db, broker):
    with db.transaction():
        db.orders.insert(order)
    broker.publish("orders.placed", {"order_id": order.id, "total": str(order.total)})
```

**Good** — the event row commits with the order; a relay publishes the rows of `outbox` and marks each one sent only after the broker confirms it, so a row can be published twice and consumers deduplicate by `event_id`:

```python
def place_order(order, db):
    with db.transaction():
        db.orders.insert(order)
        db.outbox.insert(
            event_id=new_event_id(),
            topic="orders.placed",
            key=order.id,
            payload={"order_id": order.id, "total": str(order.total)},
        )
```

## Consuming

- **Duplicates under at-least-once delivery**: brokers, queues and webhook senders deliver a message again after a crash, a timeout, a missing acknowledgement or a rebalance. A consumer whose side effect is not idempotent, such as charging a card, sending an email or inserting a row without a unique key, repeats it. Deduplicate by the event ID in the same transaction as the effect, or pass an idempotency key that the target honors. **Not a finding:** an effect that a repeat cannot change, such as setting a field to a value carried by the event when the events of that key arrive in order.
- **Acknowledged before the work is durable**: acknowledging a message, committing its offset, deleting it from the queue or answering a webhook with a `2xx` status before the work is done or stored loses the message when the consumer stops in between. **Not a finding:** a consumer that first stores the message durably, for example as a row of a job table, and acknowledges after that.
- **Order assumed but not guaranteed**: transports keep order at most within one partition, stream, queue or message group, and only while one consumer handles it one message at a time. Parallel workers, retries that put a message back behind later ones, several producers, an Amazon SQS standard queue or a change in partitioning reorder events, and a consumer that sets state from each event then lets an older event overwrite a newer one. Compare a version or sequence number before applying an event, or design the handler so that order does not matter. **Not a finding:** events of one key that the transport orders and the consumer handles one at a time.
- **Messages that always fail**: a message that can never be processed, such as a malformed body or a reference to a deleted record, either loops forever, blocking its partition or burning CPU, or disappears when the code catches the error and acknowledges it. Bound the retries and move the message where someone can see it: a dead-letter queue, a parking table or an alert. **Not a finding:** a queue whose configuration in the repository already moves the message after a bounded number of attempts (see Precedents).

**Bad** — the message is acknowledged before the charge, so a crash during `charge` loses the payment for good:

```js
consumer.on("message", async (message) => {
  message.ack();
  const event = JSON.parse(message.body);
  await payments.charge(event.orderId, event.amount);
});
```

**Good** — the acknowledgement comes after the charge; a charge that throws is delivered again, and a redelivery after a crash between the charge and the acknowledgement reuses the event ID as the idempotency key, which the payment API deduplicates within its retention window:

```js
consumer.on("message", async (message) => {
  const event = JSON.parse(message.body);
  await payments.charge(event.orderId, event.amount, { idempotencyKey: event.eventId });
  message.ack();
});
```

## Event Contracts

- **Breaking change to a published event**: removing or renaming a field, changing its type, unit or meaning, or making a new field required breaks every consumer that still reads the old shape: another service, a consumer deployed after the producer, the messages already in the queue when the change deploys, and stored events that are replayed. A version field, a schema registry with a compatibility rule, tolerant readers and upcasters are ways to keep compatibility; none of them is required by itself. **Not a finding:** an added optional field that every consumer ignores when it does not know it, or an event with no consumer outside the change and no message in flight.
- **Event-sourced state rebuilt differently**: in an event-sourced aggregate, changing how an existing event type applies to the state, or dropping the handler for it, changes the state rebuilt from every stored event of that type, so existing aggregates load with values different from the ones they had. Add a new event type or an upcaster for the new meaning, and keep the old handler. **Not a finding:** a change whose new result is the intended state for every stored event, shipped deliberately as a correction.

## Conventions, not defects

- Past-tense event names, an envelope format such as CloudEvents, a version field in every event, a schema registry, a dead-letter queue, choreography or orchestration, and thin or full event payloads are design choices; their absence is a finding only through a concrete loss, loop or broken consumer from the items above.

## Sources

- Kinds of event-driven designs: Martin Fowler, "What do you mean by Event-Driven?", https://martinfowler.com/articles/201701-event-driven.html
- Transactional outbox and idempotent consumers: Chris Richardson, microservices.io, https://microservices.io/patterns/data/transactional-outbox.html and https://microservices.io/patterns/communication-style/idempotent-consumer.html
- Delivery semantics and what Kafka's exactly-once covers: Apache Kafka documentation, https://kafka.apache.org/documentation/#semantics
- At-least-once delivery and best-effort ordering, and dead-letter redrive: Amazon SQS Developer Guide, https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html and https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
- Redelivery and ordering: RabbitMQ reliability guide, https://www.rabbitmq.com/docs/reliability
- Tolerant readers: Martin Fowler, "TolerantReader", https://martinfowler.com/bliki/TolerantReader.html
- Event envelope format: CloudEvents specification, https://github.com/cloudevents/spec

## Precedents

- **Order within one key on an ordered transport**: when the transport orders messages within a partition, stream or message group, and the consumer handles each of them one message at a time, the events that one producer publishes with the same key arrive in the order they were published. Do not report reordering of such events. **Exception:** events published by several producers or without the key, retries that requeue or republish a failed message behind later ones, a consumer that processes the messages of one partition in parallel, a change in partitioning, or a transport that does not promise order, such as an Amazon SQS standard queue.
- **A redrive limit that the repository configures**: when the queue configuration that the repository manages moves a message to a dead-letter queue after a bounded number of receives, such as an Amazon SQS redrive policy with `maxReceiveCount`, a consumer that fails on a poison message does not loop forever. Do not report an endless retry loop for such a consumer. **Exception:** the consumer catches the error and sends the message again itself, which starts a new count, the dead-letter queue is missing or not attached to this queue, or the consumer keeps extending the message's visibility timeout.
- **Idempotent targets**: a side effect keyed by the event's ID or a business key, at a target that rejects or ignores repeats (a unique constraint, a conditional write, an idempotency key that the target API honors), does not repeat when the event does. Do not report duplicate processing for such an effect. **Exception:** the key changes between deliveries (a value generated per attempt, such as a new UUID or a timestamp), the deduplication record is written outside the transaction of the effect, or the target forgets keys before the redeliveries stop.
