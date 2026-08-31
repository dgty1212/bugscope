from app.services.java_ast_parser import (
    extract_java_method_calls,
)


def test_extract_service_call() -> None:
    content = """
public class UserController {

    private final UserService userService =
        new UserService();

    public String getUser(Long id) {
        return userService.getUserName(id);
    }
}
"""

    calls = extract_java_method_calls(content)

    target = next(
        call
        for call in calls
        if call.callee_name == "getUserName"
    )

    assert target.caller_class == "UserController"
    assert target.caller_method == "getUser"

    assert target.receiver == "userService"

    assert (
        target.inferred_callee_class
        == "UserService"
    )


def test_extract_same_class_call() -> None:
    content = """
public class UserService {

    public String getUser(Long id) {
        return getUserName(id);
    }

    public String getUserName(Long id) {
        return "Alice";
    }
}
"""

    calls = extract_java_method_calls(content)

    target = next(
        call
        for call in calls
        if call.callee_name == "getUserName"
    )

    assert target.caller_class == "UserService"

    assert (
        target.inferred_callee_class
        == "UserService"
    )