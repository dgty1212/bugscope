package com.example.bugscope.sample;

import java.util.HashMap;
import java.util.Map;

public class UserService {

    private final Map<Long, String> users = new HashMap<>();

    public UserService() {
        users.put(1L, "Alice");
        users.put(2L, "Bob");
    }

    public String getUserName(Long userId) {
        String userName = users.get(userId);

        // 테스트용 잠재 오류:
        // 존재하지 않는 userId를 전달하면 userName이 null이 되어
        // NullPointerException이 발생할 수 있습니다.
        return userName.toUpperCase();
    }

    public boolean exists(Long userId) {
        return users.containsKey(userId);
    }

    public static void main(String[] args) {
        UserService service = new UserService();

        System.out.println(service.getUserName(1L));
        System.out.println(service.getUserName(999L));
    }
}
