package com.example.bugscope.benchmark.profile;
import java.util.HashMap; import java.util.Map;
public class AccountService {
    private final Map<Long,String> names = new HashMap<>();
    public AccountService() { names.put(1L,"alice-account"); }
    public String getAccountName(Long userId) { String v=names.get(userId); return v==null?"unknown":v; }
}
