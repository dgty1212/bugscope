package com.example.bugscope.benchmark.v3;

public class AlderGate {
    private final CedarUnit next = new CedarUnit();

    public int execute(String value, int expected) {
        int result = next.transform(value);
        if (result != expected) {
            throw new IllegalStateException("result contract violated");
        }
        return result;
    }
}
