# Kafka / RabbitMQ / Message Brokers — Code Review Checklist

> These items are about producers and consumers of Apache Kafka, through the Java client or librdkafka-based clients (confluent-kafka-python, -go and -dotnet, node-rdkafka), and of RabbitMQ through AMQP 0-9-1 clients. Defaults differ between clients and versions: read the client library and its version from the manifest or lockfile, and the configuration that the code passes, before applying a default named below. Broker and topic settings often live outside the repository; when a finding depends on one, say so. Check sibling producers and consumers for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code.

## Kafka Consumers

- **Offsets committed before processing**: a commit that covers a record before its processing ends loses the record when the consumer crashes in between. The Java client commits automatically by default (`enable.auto.commit=true`, every 5 seconds); the committed offset gets ahead of the processed records when the code hands records to another thread or queue and calls `poll()` again before they are processed. librdkafka-based clients, with their defaults (`enable.auto.commit=true` and `enable.auto.offset.store=true`), store the offset of each message when they return it to the application and commit stored offsets in the background, so a crash while a returned message is still being processed can skip it. Set `enable.auto.offset.store=false` and call `store_offsets()` after processing, or turn auto-commit off and commit after processing. **Not a finding:** a Java consumer with auto-commit that processes every record of a `poll()` before its next call, which gives at-least-once delivery.
- **Repeated side effects**: committing after processing gives at-least-once delivery, so a crash or rebalance between the side effect and the commit delivers the record again. A consumer whose side effect is not idempotent, such as charging a card, sending an email or inserting a row without a unique key, repeats it. **Not a finding:** side effects keyed by a unique message or business ID that the target rejects or ignores when it sees it again.
- **Processing longer than `max.poll.interval.ms`**: when the time between two `poll()` calls exceeds `max.poll.interval.ms` (5 minutes by default in the Java client and in librdkafka), a consumer that uses group management leaves the group and its partitions move to other members. A manually assigned consumer (`assign()`) has no such group reassignment. With a non-null `group.instance.id` (static membership), its partitions stay assigned until the session timeout expires. When a rebalance does reassign them, the Java client's next `commitSync()` may throw `CommitFailedException`, and the new owner processes the uncommitted records again, which repeats on every rebalance while a batch keeps taking longer than the interval. Bound the work per poll (`max.poll.records` in the Java client) or the processing time, or raise the interval.
- **Records of aborted transactions**: the Java consumer reads with `isolation.level=read_uncommitted` by default, which also returns records that a transactional producer wrote in transactions it later aborted. A consumer that must see only committed results needs `read_committed`. **Not a finding:** librdkafka-based consumers, which default to `read_committed`, and topics that no transactional producer writes.

**Bad** — the background auto-commit can commit an offset whose `charge` has not finished, so a crash loses that order:

```python
from concurrent.futures import ThreadPoolExecutor

from confluent_kafka import Consumer

from billing import charge

executor = ThreadPoolExecutor(max_workers=8)
consumer = Consumer({"bootstrap.servers": "kafka:9092", "group.id": "billing"})
consumer.subscribe(["orders"])

while True:
    msg = consumer.poll(1.0)
    if msg is None or msg.error():
        continue
    executor.submit(charge, msg.value())
```

**Good** — the offset is stored only after `charge` returns, and the background auto-commit commits only stored offsets; `charge` must tolerate a repeated order:

```python
from confluent_kafka import Consumer

from billing import charge

consumer = Consumer({
    "bootstrap.servers": "kafka:9092",
    "group.id": "billing",
    "enable.auto.offset.store": False,
})
consumer.subscribe(["orders"])

while True:
    msg = consumer.poll(1.0)
    if msg is None or msg.error():
        continue
    charge(msg.value())
    consumer.store_offsets(message=msg)
```

## Kafka Producers

- **Unchecked sends**: `send()` in the Java client and `produce()` in librdkafka-based clients are asynchronous: they return before the broker has the record, and a failure is reported only through the returned `Future`, the callback or the delivery report, for example when `delivery.timeout.ms` (2 minutes by default in the Java client) or `message.timeout.ms` (5 minutes by default in librdkafka) expires. Code that ignores them reports success for records that were never written. In confluent-kafka-python (and the librdkafka C API), delivery callbacks run only from `poll()` or `flush()`. The Go client emits delivery reports on the `Events()` channel, or on the channel passed to `Produce()`, which the application must read. The .NET client serves them on a background thread by default (`EnableBackgroundPoll`, `true`), so code that awaits `ProduceAsync` needs no poll call; `Poll` is needed only when that is disabled. Records still queued when the process exits without `flush()` may never be sent.
- **Weaker acknowledgements**: with `acks=0` or `acks=1`, the producer reports success before the followers have the record, so a leader failure can lose acknowledged records. `acks=all` is the default in the Java client since 3.0 and in librdkafka. Even with `acks=all`, a topic whose `min.insync.replicas` is 1 (the default) accepts a write that only the leader holds. Report a change that lowers `acks`, or the replication settings that the repository manages, for data that must not be lost.
- **Database and broker writes without a shared transaction**: writing to a database and producing an event as two separate steps loses one of them when the process fails between them: the event describes a change that was rolled back, or a committed change never produces its event. Kafka transactions cover Kafka writes and consumer offsets, not the database. Write the event to an outbox table in the same database transaction and publish it from there, or make consumers reconcile from the database. **Not a finding:** events whose loss or duplication the consumers already tolerate.

**Bad** — the function returns while records are still queued, and a failed delivery is never seen:

```python
from confluent_kafka import Producer


def publish_invoices(invoices):
    producer = Producer({"bootstrap.servers": "kafka:9092"})
    for invoice in invoices:
        producer.produce("invoices", key=invoice.id, value=invoice.to_json())
```

**Good** — delivery reports are collected, `flush()` waits for them, and any failure raises:

```python
from confluent_kafka import Producer


def publish_invoices(invoices):
    producer = Producer({"bootstrap.servers": "kafka:9092"})
    failures = []

    def on_delivery(err, msg):
        if err is not None:
            failures.append(err)

    for invoice in invoices:
        producer.produce("invoices", key=invoice.id, value=invoice.to_json(), on_delivery=on_delivery)
        producer.poll(0)
    remaining = producer.flush(30)
    if remaining or failures:
        raise RuntimeError(f"{remaining} invoice(s) undelivered, {len(failures)} failed")
```

## RabbitMQ

- **Publishing without confirms**: `basic.publish` does not wait for the broker, so without publisher confirms (or transactions) a connection or node failure loses messages that the publisher believes were sent, and a node can lose persistent messages that it has not yet written to disk. A message that no queue matches, published without the `mandatory` flag, is discarded unless an alternate exchange receives it. For messages that must not be lost, enable confirms and handle negative acknowledgements and returned messages.
- **Durability**: a message in a classic queue survives a node restart only when it is published as persistent (`delivery_mode=2`) to a durable queue; transient messages are discarded during recovery even in durable queues, and transient queues are deleted. Quorum queues are always durable. **Not a finding:** data that the application accepts losing on a restart.
- **No prefetch limit**: with manual acknowledgements, a prefetch of `0` means no limit, so the broker sends a consumer every message it can deliver, and the consumer holds all of them in memory while it works through them. Set a prefetch limit with `basic.qos` (or the client's equivalent), and check the broker's `default_consumer_prefetch` when the code sets none.
- **Requeue loops**: `basic.nack` or `basic.reject` with `requeue=true` for a message that will always fail, such as a malformed body or a reference to a deleted record, returns it to the queue to be delivered again at once, in a loop that costs CPU and network and can delay other messages. Classic queues never stop the loop. Quorum queues drop the message, or dead-letter it when a dead-letter exchange is configured, after its delivery limit (20 by default since RabbitMQ 4.0), but since RabbitMQ 4.3 `basic.nack` no longer counts toward that limit. Reject permanent failures with `requeue=false` to a dead-letter exchange, and limit retries of transient failures with a retry count or a delay.
- **Acknowledging on the wrong channel or twice**: a delivery tag belongs to the channel that delivered the message. Acknowledging it on another channel, or twice, raises a channel error (`PRECONDITION_FAILED - unknown delivery tag`) that closes the channel, and the channel's other unacknowledged messages are delivered again.

**Bad** — a message that always fails comes back at once and loops forever:

```python
import json

from orders import handle


def on_message(channel, method, properties, body):
    try:
        handle(json.loads(body))
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
```

**Good** — with the queue declared with an `x-dead-letter-exchange`, a failed message moves there for inspection or a delayed retry, and the acknowledgement stays outside the `try` so that it is never followed by a reject:

```python
import json

from orders import handle


def on_message(channel, method, properties, body):
    try:
        handle(json.loads(body))
    except Exception:
        channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        return
    channel.basic_ack(delivery_tag=method.delivery_tag)
```

## Conventions, not defects

- A dead-letter queue, a schema registry and the message format (JSON, Avro, Protobuf) are design choices; their absence is a finding only through a concrete loss or loop from the items above, or when the change removes or renames a field that an existing consumer reads.
- The client library, the consumer framework and naming of topics, queues and exchanges follow the repository's conventions.

## Sources

- Java consumer offsets, auto-commit, liveness and `CommitFailedException`: https://kafka.apache.org/39/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html
- Java client and topic configuration: https://kafka.apache.org/44/configuration/consumer-configs/, https://kafka.apache.org/44/configuration/producer-configs/, https://kafka.apache.org/44/configuration/topic-configs/
- Producer defaults since 3.0: https://cwiki.apache.org/confluence/display/KAFKA/KIP-679%3A+Producer+will+enable+the+strongest+delivery+guarantee+by+default
- Kafka transactions: https://kafka.apache.org/39/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html
- librdkafka configuration: https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md; confluent-kafka-python `produce`, `flush`, `store_offsets`: https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html
- Delivery reports in Go and .NET, and librdkafka's delivery callback served by `rd_kafka_poll()`: https://pkg.go.dev/github.com/confluentinc/confluent-kafka-go/v2/kafka, https://docs.confluent.io/platform/current/clients/confluent-kafka-dotnet/_site/api/Confluent.Kafka.ProducerConfig.html, https://github.com/confluentinc/librdkafka/blob/master/src/rdkafka.h
- RabbitMQ acknowledgements, confirms, prefetch and requeueing: https://www.rabbitmq.com/docs/confirms, https://www.rabbitmq.com/docs/consumer-prefetch
- RabbitMQ publishers and unroutable messages: https://www.rabbitmq.com/docs/publishers; queue durability: https://www.rabbitmq.com/docs/queues; quorum queues and delivery limits: https://www.rabbitmq.com/docs/quorum-queues; dead-lettering: https://www.rabbitmq.com/docs/dlx

## Precedents

- **Kafka keeps order within a partition**: a producer using the default key-based partitioner sends records with the same non-null key to the same partition while the topic's partition count stays the same, and one consumer in the group reads each partition in order. Do not report reordering of records that one such producer sends with the same key. **Exception:** keyless records, records sent with an explicit partition, a custom or round-robin partitioner or `partitioner.ignore.keys=true`, producers of the same key that partition differently (for example clients with different hash functions), records from different producers, whose relative order Kafka never fixes, a change in the topic's partition count, producers that are not idempotent and have more than one request in flight with retries — idempotence is off by default in Java clients before 3.0, in librdkafka-based clients (confluent-kafka-python, -go and -dotnet, node-rdkafka) unless `enable.idempotence=true`, and in KafkaJS, an explicit `enable.idempotence=false` turns it off, and Java 3.x clients disable it silently when `acks` is not `all` or when `max.in.flight.requests.per.connection` exceeds 5 — and consumers that hand records to parallel workers.
- **RabbitMQ requeues unacknowledged deliveries**: with manual acknowledgements, a delivery that is not acked when the consumer's channel or connection closes is returned to the queue and can be delivered again. Do not report a manual-ack consumer crash, by itself, as losing the message. **Exception:** consumers with automatic acknowledgement (`autoAck` or `noAck: true`), messages rejected or nacked with `requeue=false`, quorum queues whose delivery limit (20 by default since RabbitMQ 4.0) repeated crashes exhaust, and message TTL or length limits, each of which drops the message unless a dead-letter exchange receives it; and queue expiry, explicit queue deletion, exclusive queues (deleted when the declaring connection closes) or auto-delete queues (deleted when the last consumer leaves), which discard their queued messages without dead-lettering them.
