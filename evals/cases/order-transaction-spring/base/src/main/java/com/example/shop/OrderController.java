package com.example.shop;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {
    private final OrderService orders;

    public OrderController(OrderService orders) {
        this.orders = orders;
    }

    public record OrderRequest(String sku, int quantity) {
    }

    @PostMapping("/orders")
    public Order create(@RequestBody OrderRequest request) {
        return orders.placeOrder(request.sku(), request.quantity());
    }
}
