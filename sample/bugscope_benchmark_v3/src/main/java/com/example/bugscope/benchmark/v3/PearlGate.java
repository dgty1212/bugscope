package com.example.bugscope.benchmark.v3;

public class PearlGate {
    private final QuartzLink next = new QuartzLink();

    public int execute(String value, int expected) {
        int result = next.forward(value);
        if (result != expected) {
            throw new IllegalStateException("result contract violated");
        }
        return result;
    }
}
