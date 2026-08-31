package com.example.bugscope.sample;

import java.time.Instant;

public class AuditService {
    public String createLog(String action) {
        return Instant.now() + " action=" + action;
    }
}
