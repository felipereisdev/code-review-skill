package com.example.shop;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;

@Entity
public class StockItem {
    @Id
    private String sku;
    private int available;

    protected StockItem() {
    }
}
