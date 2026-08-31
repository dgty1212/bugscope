package com.example.bugscope.benchmark.reports;
public class ReportFormatter {
    public String formatAverage(double average) { return String.format("%.2f",average); }
    public String formatTitle(String title) { return title==null?"":title.trim(); }
}
