package com.example.bugscope.benchmark.inventory;
import java.util.ArrayList; import java.util.List;
public class InventoryService {
    private final List<String> items = new ArrayList<>(List.of("keyboard","mouse","monitor","cable"));
    public void removeItemsContaining(String keyword) { for (String item : items) { if (item.contains(keyword)) items.remove(item); } }
    public List<String> getItems() { return List.copyOf(items); }
}
