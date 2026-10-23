# Kafka / RabbitMQ / Message Brokers — Code Review Checklist

- **Idempotent consumers**: duplicate message delivery handled correctly; no double-processing side effects
- **Dead letter queue**: messages that fail processing after retries are routed to a DLQ, not dropped
- **Schema evolution**: message schemas are backward-compatible or versioned; consumers handle unknown fields
- **Ordering**: consumers that require ordering use a single partition/queue or handle reordering explicitly
- **Acknowledgement**: messages acknowledged only after successful processing, not before
- **Poison pill handling**: malformed messages do not block the queue indefinitely

## Precedents

- **Kafka keeps order within a partition**: a producer using the default key-based partitioner sends records with the same non-null key to the same partition while the topic's partition count stays the same, and one consumer in the group reads each partition in order. Do not report reordering of records that one such producer sends with the same key. **Exception:** keyless records, records sent with an explicit partition, a custom or round-robin partitioner or `partitioner.ignore.keys=true`, producers of the same key that partition differently (for example clients with different hash functions), records from different producers, whose relative order Kafka never fixes, a change in the topic's partition count, producers with `enable.idempotence=false` and more than one in-flight request with retries, and consumers that hand records to parallel workers.
- **RabbitMQ requeues unacknowledged deliveries**: with manual acknowledgements, a delivery that is not acked when the consumer's channel or connection closes is returned to the queue and can be delivered again. Do not report a manual-ack consumer crash, by itself, as losing the message. **Exception:** consumers with automatic acknowledgement (`autoAck` or `noAck: true`), messages rejected or nacked with `requeue=false`, quorum queues whose delivery limit (20 by default since RabbitMQ 4.0) repeated crashes exhaust, and message TTL, queue expiry, length limits or queue deletion; each of these drops the message unless a dead-letter exchange receives it.
