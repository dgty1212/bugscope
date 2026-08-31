package com.example.bugscope.benchmark.cache;
import java.util.HashMap; import java.util.Map;
public class UserCacheService {
    private final Map<Long,String> userCache = new HashMap<>();
    public String findUserName(Long userId) { return userCache.get(userId); }
    public void putUser(Long userId,String userName) { userCache.put(userId,userName); }
}
