package com.example.bugscope.benchmark.users;
public class UserValidator {
    public void validateUserId(Long userId) { if (userId == null || userId <= 0) throw new IllegalArgumentException("invalid user id"); }
    public boolean looksValid(Long userId) { return userId != null && userId > 0; }
}
