package com.example.bugscope.benchmark.orders;
public class OrderController {
    private final OrderService orderService = new OrderService();
    public String getOrder(int position) { return orderService.getOrderByPosition(position); }
}
