package com.example.bugscope.benchmark.files;
import java.nio.file.Path;
public class UploadService { public Path resolveUpload(String name) { return Path.of("uploads").resolve(name).normalize(); } }
