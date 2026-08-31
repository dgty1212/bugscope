package com.example.bugscope.benchmark.misc;
import java.util.List;
public class CollectionUtilityService {
    public String safeGet(List<String> values,int index) { if(index < 0 || index >= values.size()) return null; return values.get(index); }
}
