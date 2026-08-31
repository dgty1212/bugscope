package com.example.bugscope.benchmark.config;
public class EnvironmentConfig {
    public int parsePort(String value) { if (value == null || value.isBlank()) return 8080; return Integer.parseInt(value); }
    public String normalizeProfile(String profile) { return profile == null ? "default" : profile.trim(); }
}
