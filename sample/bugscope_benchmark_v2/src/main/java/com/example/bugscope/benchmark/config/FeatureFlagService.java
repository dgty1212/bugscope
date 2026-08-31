package com.example.bugscope.benchmark.config;
import java.util.Map;
public class FeatureFlagService {
    private final Map<String,String> flags = Map.of("new-ui","true","beta-search","false");
    public boolean isEnabled(String name) { return Boolean.parseBoolean(flags.getOrDefault(name,"false")); }
}
