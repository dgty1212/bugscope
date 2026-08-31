package com.example.bugscope.benchmark.payments;
import java.math.BigDecimal;
public class PaymentService {
    public BigDecimal calculateDiscountedPrice(BigDecimal price, BigDecimal discountRate) {
        if (discountRate.compareTo(BigDecimal.ZERO) < 0) throw new IllegalArgumentException("discountRate must be non-negative");
        return price.subtract(price.multiply(discountRate));
    }
    public BigDecimal charge(BigDecimal amount) {
        if (amount.signum() <= 0) throw new IllegalArgumentException("amount must be positive");
        return amount;
    }
}
