package com.example.bugscope.benchmark.users;
import java.util.HashMap; import java.util.Map;
public class UserRepository {
    private final Map<Long,String> rows = new HashMap<>();
    public UserRepository() { rows.put(1L,"Alice"); rows.put(2L,"Bob"); }
    public String findNameById(Long userId) { return rows.get(userId); }
    public boolean existsById(Long userId) { return rows.containsKey(userId); }
}
