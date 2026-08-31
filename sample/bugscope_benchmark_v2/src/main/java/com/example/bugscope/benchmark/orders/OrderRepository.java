package com.example.bugscope.benchmark.orders;
import java.util.List;
public class OrderRepository {
    private final List<String> rows = List.of("ORDER-1001","ORDER-1002","ORDER-1003");
    public List<String> findAll() { return rows; }
    public String findFirst() { return rows.get(0); }
}
