package com.example.bugscope.benchmark.v3;

public class JadeGate {
    private final LarchUnit next = new LarchUnit();

    public int execute(String value, int expected) {
        int result = next.transform(value);
        if (result != expected) {
            throw new IllegalStateException("result contract violated");
        }
        return result;
    }
}
