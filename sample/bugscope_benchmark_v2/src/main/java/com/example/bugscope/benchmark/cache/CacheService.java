package com.example.bugscope.benchmark.cache;
import java.util.HashMap; import java.util.Map;
public class CacheService {
    private final Map<String,String> cache = new HashMap<>();
    public String getUppercase(String key) { String value=cache.get(key); return value.toUpperCase(); }
    public void put(String key,String value) { cache.put(key,value); }
}
