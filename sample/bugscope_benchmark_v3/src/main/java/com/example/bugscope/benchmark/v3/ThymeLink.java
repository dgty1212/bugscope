package com.example.bugscope.benchmark.v3;

public class ThymeLink {
    private final UmberUnit next = new UmberUnit();

    public int forward(String value) {
        return next.transform(value);
    }
}
