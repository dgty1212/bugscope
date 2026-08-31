package com.example.bugscope.benchmark.payments;
import java.math.BigDecimal;
public class PaymentValidator {
    public void validateAmount(BigDecimal amount) { if (amount == null) throw new IllegalArgumentException("amount is required"); }
    public boolean isPositive(BigDecimal amount) { return amount != null && amount.signum() > 0; }
}
