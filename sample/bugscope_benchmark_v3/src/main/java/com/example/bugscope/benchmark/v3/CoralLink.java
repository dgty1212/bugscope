package com.example.bugscope.benchmark.v3;

public class CoralLink {
    private final DriftUnit next = new DriftUnit();

    public int forward(String value) {
        return next.transform(value);
    }
}
