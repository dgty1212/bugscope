package com.example.bugscope.benchmark.dates;
public class DateValidator { public boolean looksIsoDate(String value) { return value != null && value.matches("\\d{4}-\\d{2}-\\d{2}"); } }
