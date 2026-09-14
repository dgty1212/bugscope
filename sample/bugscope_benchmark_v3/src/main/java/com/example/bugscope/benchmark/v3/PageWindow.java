package com.example.bugscope.benchmark.v3;

public class PageWindow {
    // The first page of a one-based paginated list skips the first batch of rows.
    public int offset(int page, int size) {
        return page * size;
    }
}
