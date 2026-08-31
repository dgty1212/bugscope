package com.example.bugscope.sample;

public class AuthService {
    public String extractBearerToken(String authorizationHeader) {
        return authorizationHeader.substring(7);
    }

    public boolean isBearerToken(String authorizationHeader) {
        return authorizationHeader != null
            && authorizationHeader.startsWith("Bearer ");
    }
}
