package com.example.bugscope.benchmark.v3;

public class WillowLink {
    private final XeniaUnit next = new XeniaUnit();

    public int forward(String value) {
        return next.transform(value);
    }
}
