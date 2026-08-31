package com.example.bugscope.benchmark.notification;
public class EmailService {
    public String extractDomain(String email) { int at=email.indexOf("@"); return email.substring(at+1); }
}
