package com.example.bugscope.benchmark.auth;
public class TokenService {
    public String normalizeToken(String token) { if(token==null) return ""; return token.trim(); }
    public boolean isEmpty(String token) { return token==null || token.isBlank(); }
}
