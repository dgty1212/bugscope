package com.example.bugscope.sample;

import java.util.HashMap;
import java.util.Map;

public class ProfileService {
    private final Map<Long, String> emails = new HashMap<>();

    public ProfileService() {
        emails.put(1L, "alice@example.com");
    }

    public String getEmailDomain(Long userId) {
        String email = emails.get(userId);
        int atIndex = email.indexOf("@");
        return email.substring(atIndex + 1);
    }
}
