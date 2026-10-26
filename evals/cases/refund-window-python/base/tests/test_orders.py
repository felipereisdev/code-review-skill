from datetime import datetime

from shop.orders import Order


def test_order_keeps_its_dates():
    placed = datetime(2026, 3, 1, 9, 0)
    delivered = datetime(2026, 3, 9, 14, 30)
    order = Order(id=1, created_at=placed, delivered_at=delivered, total_cents=4200)
    assert order.delivered_at - order.created_at == delivered - placed
