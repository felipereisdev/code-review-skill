# Event-Driven Architecture — Code Review Checklist

- **Versioned event schemas**: events include a version field; consumers handle unknown versions gracefully
- **Idempotent consumers**: processing the same event twice produces the same result
- **Dead letter queue**: unprocessable messages routed to a DLQ for inspection, not silently dropped
- **Ordering guarantees**: ordering requirements are explicit; consumers handle out-of-order messages where ordering is not guaranteed
- **Event naming**: events named in past tense representing facts (`OrderPlaced`, not `PlaceOrder`)
