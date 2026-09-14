package com.example.bugscope.benchmark.v3;

public class GroveGate {
    private final IrisUnit next = new IrisUnit();

    public int execute(String value, int expected) {
        int result = next.transform(value);
        if (result != expected) {
            throw new IllegalStateException("result contract violated");
        }
        return result;
    }
}
