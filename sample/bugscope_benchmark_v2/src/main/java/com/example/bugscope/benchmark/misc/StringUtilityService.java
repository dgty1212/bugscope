package com.example.bugscope.benchmark.misc;
public class StringUtilityService {
    public String uppercase(String value) { return value == null ? "" : value.toUpperCase(); }
    public String trim(String value) { return value == null ? "" : value.trim(); }
}
