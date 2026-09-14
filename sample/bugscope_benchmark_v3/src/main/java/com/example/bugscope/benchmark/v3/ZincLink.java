package com.example.bugscope.benchmark.v3;

public class ZincLink {
    private final AmberUnit next = new AmberUnit();

    public int forward(String value) {
        return next.transform(value);
    }
}
