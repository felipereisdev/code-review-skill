package com.example.shop;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface StockRepository extends JpaRepository<StockItem, String> {
    @Modifying
    @Query("UPDATE StockItem s SET s.available = s.available - :quantity WHERE s.sku = :sku AND s.available >= :quantity")
    int decrement(@Param("sku") String sku, @Param("quantity") int quantity);
}
