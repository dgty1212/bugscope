package com.example.bugscope.sample;

import java.util.List;

public class OrderService {
    private final List<String> orders = List.of(
        "ORDER-1001",
        "ORDER-1002",
        "ORDER-1003"
    );

    public String getOrderByPosition(int position) {
        return orders.get(position);
    }

    public String getFirstOrder() {
        return orders.get(0);
    }
}
