package com.example.bugscope.sample;

import java.util.Map;

public class ConfigLoader {
    private final Map<String, String> values = Map.of(
        "server.port", "8080",
        "worker.count", "four"
    );

    public int getWorkerCount() {
        String value = values.get("worker.count");
        return Integer.parseInt(value);
    }

    public int getServerPort() {
        return Integer.parseInt(values.get("server.port"));
    }
}
