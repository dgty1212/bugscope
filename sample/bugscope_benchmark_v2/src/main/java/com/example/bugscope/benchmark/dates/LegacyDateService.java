package com.example.bugscope.benchmark.dates;
import java.time.LocalDate; import java.time.format.DateTimeFormatter;
public class LegacyDateService {
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("dd/MM/yyyy");
    public LocalDate parseLegacyDate(String value) { return LocalDate.parse(value,FORMATTER); }
}
