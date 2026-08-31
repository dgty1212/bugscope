package com.example.bugscope.benchmark.payments;
import java.math.BigDecimal;
public class RefundService {
    public BigDecimal refund(BigDecimal amount) { if (amount == null) throw new IllegalArgumentException("refund amount required"); return amount.negate(); }
}
