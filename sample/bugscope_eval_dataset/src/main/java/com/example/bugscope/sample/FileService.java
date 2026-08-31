package com.example.bugscope.sample;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public class FileService {
    public String readReport(String fileName) throws IOException {
        Path path = Path.of("reports", fileName);
        return Files.readString(path);
    }

    public boolean reportExists(String fileName) {
        return Files.exists(Path.of("reports", fileName));
    }
}
