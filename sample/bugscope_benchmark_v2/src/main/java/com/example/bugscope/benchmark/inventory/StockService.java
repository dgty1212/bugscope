package com.example.bugscope.benchmark.inventory;
import java.util.HashMap; import java.util.Map;
public class StockService {
    private final Map<String,Integer> stock = new HashMap<>();
    public StockService() { stock.put("keyboard",5); }
    public int getStock(String sku) { return stock.getOrDefault(sku,0); }
}
