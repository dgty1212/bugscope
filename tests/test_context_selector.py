from app.services.context_selector import (
    SelectedContext,
    context_key,
)


def test_same_location_has_same_context_key() -> None:
    first = SelectedContext(
        context_type="trace",
        source_type="symbol",
        source_id=1,
        file_path="src/UserService.java",
        class_name="UserService",
        symbol_name="getUserName",
        start_line=10,
        end_line=20,
        content="method",
    )

    second = SelectedContext(
        context_type="semantic",
        source_type="chunk",
        source_id=50,
        file_path="src/UserService.java",
        class_name=None,
        symbol_name=None,
        start_line=10,
        end_line=20,
        content="method",
        score=0.9,
    )

    assert context_key(first) == context_key(
        second
    )