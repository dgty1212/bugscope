package com.example.bugscope.benchmark.inventory;
import java.util.ArrayList; import java.util.List;
public class InventoryRepository {
    private final List<String> items = new ArrayList<>(List.of("keyboard","mouse","monitor","cable"));
    public void delete(String item) { items.remove(item); }
    public List<String> findAll() { return List.copyOf(items); }
}
