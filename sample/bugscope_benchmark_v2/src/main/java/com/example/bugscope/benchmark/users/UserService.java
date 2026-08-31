package com.example.bugscope.benchmark.users;

import java.util.HashMap;
import java.util.Map;

public class UserService {
    private final Map<Long, String> users = new HashMap<>();
    public UserService() { users.put(1L, "Alice"); users.put(2L, "Bob"); }
    public String getUserName(Long userId) {
        String userName = users.get(userId);
        return userName.toUpperCase();
    }
    public boolean exists(Long userId) { return users.containsKey(userId); }
}
