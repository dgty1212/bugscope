from app.services.stack_trace_parser import (
    parse_stack_trace,
)


def test_parse_java_stack_trace() -> None:
    error_log = """
java.lang.NullPointerException: userName is null
    at com.example.UserService.getUserName(UserService.java:18)
    at com.example.UserController.getUser(UserController.java:42)
"""

    parsed = parse_stack_trace(error_log)

    assert (
        parsed.exception_type
        == "java.lang.NullPointerException"
    )

    assert len(parsed.frames) == 2

    first = parsed.frames[0]

    assert first.class_name == "UserService"
    assert first.method_name == "getUserName"
    assert first.file_name == "UserService.java"
    assert first.line_number == 18
    assert first.depth == 0


def test_parse_unknown_source() -> None:
    error_log = """
java.lang.RuntimeException: test
    at com.example.Proxy.invoke(Unknown Source)
"""

    parsed = parse_stack_trace(error_log)

    assert len(parsed.frames) == 1

    frame = parsed.frames[0]

    assert frame.method_name == "invoke"
    assert frame.file_name is None
    assert frame.line_number is None