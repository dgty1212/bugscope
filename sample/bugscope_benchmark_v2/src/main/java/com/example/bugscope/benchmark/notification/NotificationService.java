package com.example.bugscope.benchmark.notification;
public class NotificationService {
    public String buildMessage(String userName,String message) { return "["+userName+"] "+message; }
    public boolean isEmpty(String message) { return message==null || message.isBlank(); }
}
