package com.example.bugscope.benchmark.v3;

public class QuartzLink {
    private final ReedUnit next = new ReedUnit();

    public int forward(String value) {
        return next.transform(value);
    }
}
