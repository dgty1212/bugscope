package com.example.bugscope.benchmark.files;
import java.io.IOException; import java.nio.file.Files; import java.nio.file.Path;
public class TemplateService {
    public String loadTemplate(String name) throws IOException { Path path=Path.of("templates",name+".txt"); if(!Files.exists(path)) return ""; return Files.readString(path); }
}
