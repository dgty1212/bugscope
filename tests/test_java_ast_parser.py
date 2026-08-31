from app.services.java_ast_parser import (
    extract_java_symbols,
)


def test_extract_java_symbols() -> None:
    content = """
package com.example;

public class UserService {

    public String getUserName(Long id) {
        return "Alice";
    }

    public boolean exists(Long id) {
        return true;
    }
}
"""

    symbols = extract_java_symbols(content)

    classes = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == "class"
    ]

    methods = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == "method"
    ]

    assert len(classes) == 1

    assert classes[0].symbol_name == "UserService"

    method_names = {
        method.symbol_name
        for method in methods
    }

    assert "getUserName" in method_names
    assert "exists" in method_names


def test_method_has_class_name() -> None:
    content = """
public class OrderService {

    public String getOrder(int id) {
        return "ORDER";
    }
}
"""

    symbols = extract_java_symbols(content)

    method = next(
        symbol
        for symbol in symbols
        if symbol.symbol_name == "getOrder"
    )

    assert method.class_name == "OrderService"