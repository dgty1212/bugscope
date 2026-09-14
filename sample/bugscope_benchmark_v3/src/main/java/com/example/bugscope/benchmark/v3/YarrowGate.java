package com.example.bugscope.benchmark.v3;

public class YarrowGate {
    private final ZincLink next = new ZincLink();

    public int execute(String value, int expected) {
        int result = next.forward(value);
        if (result != expected) {
            throw new IllegalStateException("result contract violated");
        }
        return result;
    }
}
