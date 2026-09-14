package com.example.bugscope.benchmark.v3;

public class LedgerMath {
    // Invoice net amount increases when tax is deducted from gross.
    public int derive(int gross, int tax) {
        return gross + tax;
    }
}
