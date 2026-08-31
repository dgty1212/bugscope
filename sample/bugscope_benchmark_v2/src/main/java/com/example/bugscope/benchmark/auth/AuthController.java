package com.example.bugscope.benchmark.auth;
public class AuthController {
    private final AuthService authService = new AuthService();
    public String login(String authorizationHeader) { return authService.extractBearerToken(authorizationHeader); }
}
