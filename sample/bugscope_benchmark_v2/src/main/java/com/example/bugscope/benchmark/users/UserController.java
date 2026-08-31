package com.example.bugscope.benchmark.users;
public class UserController {
    private final UserService userService = new UserService();
    public String getUser(Long userId) { return userService.getUserName(userId); }
    public String health() { return "ok"; }
}
