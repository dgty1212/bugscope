package com.example.bugscope.benchmark.dates;
import java.time.LocalDate; import java.time.format.DateTimeFormatter;
public class DateParserService {
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    public LocalDate parseDate(String value) { return LocalDate.parse(value,FORMATTER); }
}
