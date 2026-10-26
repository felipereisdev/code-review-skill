# Refund policy

Customers can ask for a refund of a delivered order.

## Rules

1. The refund window is 30 days and starts when the order is delivered (`Order.delivered_at`), not when it was placed. A request exactly 30 days after delivery is still accepted.
2. An order that has not been delivered yet (`delivered_at` is `None`) cannot be refunded through `is_refundable`; support cancels it instead.
3. `is_refundable(order, now)` returns `True` when a refund can be granted and `False` otherwise.
