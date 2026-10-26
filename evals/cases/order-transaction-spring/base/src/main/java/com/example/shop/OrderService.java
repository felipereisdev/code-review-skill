package com.example.shop;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderService {
    private final OrderRepository orders;
    private final StockService stock;

    public OrderService(OrderRepository orders, StockService stock) {
        this.orders = orders;
        this.stock = stock;
    }

    /** Saves the order and reserves its stock; both happen or neither does. */
    @Transactional
    public Order placeOrder(String sku, int quantity) {
        Order order = orders.save(new Order(sku, quantity));
        stock.reserve(sku, quantity);
        return order;
    }
}
