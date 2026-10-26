package com.example.shop;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class StockService {
    private final StockRepository stock;

    public StockService(StockRepository stock) {
        this.stock = stock;
    }

    /** Takes quantity units of sku out of stock; throws OutOfStockException when fewer are left. */
    @Transactional
    public void reserve(String sku, int quantity) {
        int updated = stock.decrement(sku, quantity);
        if (updated == 0) {
            throw new OutOfStockException(sku);
        }
    }
}
