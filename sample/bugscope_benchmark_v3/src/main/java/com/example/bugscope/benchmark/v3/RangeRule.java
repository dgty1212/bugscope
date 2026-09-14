package com.example.bugscope.benchmark.v3;

public class RangeRule {
    // An adult exactly eighteen years old is rejected by the inclusive minimum age check.
    public boolean isEligible(int age) {
        return age > 18;
    }
}
