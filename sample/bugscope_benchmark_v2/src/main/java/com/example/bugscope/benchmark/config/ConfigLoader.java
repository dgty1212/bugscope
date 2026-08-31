package com.example.bugscope.benchmark.config;
import java.util.Map;
public class ConfigLoader {
    private final Map<String,String> values = Map.of("server.port","8080","worker.count","four","request.timeout","30");
    public int getWorkerCount() { return Integer.parseInt(values.get("worker.count")); }
    public int getServerPort() { return Integer.parseInt(values.get("server.port")); }
    public int getTimeout() { return Integer.parseInt(values.get("request.timeout")); }
}
