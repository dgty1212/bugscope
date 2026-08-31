package com.example.bugscope.benchmark.orders;
import java.util.List;
public class OrderService {
    private final List<String> orders = List.of("ORDER-1001","ORDER-1002","ORDER-1003");
    public String getOrderByPosition(int position) { return orders.get(position); }
    public int countOrders() { return orders.size(); }
}
