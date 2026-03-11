# Kafka / RabbitMQ / Message Brokers — Code Review Checklist

- **Idempotent consumers**: duplicate message delivery handled correctly; no double-processing side effects
- **Dead letter queue**: messages that fail processing after retries are routed to a DLQ, not dropped
- **Schema evolution**: message schemas are backward-compatible or versioned; consumers handle unknown fields
- **Ordering**: consumers that require ordering use a single partition/queue or handle reordering explicitly
- **Acknowledgement**: messages acknowledged only after successful processing, not before
- **Poison pill handling**: malformed messages do not block the queue indefinitely
