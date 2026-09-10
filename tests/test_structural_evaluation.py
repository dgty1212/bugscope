from app.services.context_selector import (
    SelectedContext,
)
from app.services.structural_evaluation_service import (
    file_matches,
    hit_at_k,
    reciprocal_rank,
    symbol_matches,
)


def make_context() -> SelectedContext:
    return SelectedContext(
        context_type="trace",
        source_type="symbol",
        source_id=1,
        file_path=(
            "src/main/java/com/example/"
            "users/UserService.java"
        ),
        class_name="UserService",
        symbol_name="getUserName",
        start_line=10,
        end_line=20,
        content=(
            "public String getUserName(Long id) {"
            " return users.get(id);"
            " }"
        ),
    )


def test_file_matches_filename() -> None:
    context = make_context()

    assert file_matches(
        context,
        "UserService.java",
    )


def test_file_matches_full_path() -> None:
    context = make_context()

    assert file_matches(
        context,
        (
            "src/main/java/com/example/"
            "users/UserService.java"
        ),
    )


def test_symbol_matches_structural_symbol() -> None:
    context = make_context()

    assert symbol_matches(
        context,
        "getUserName",
    )


def test_hit_at_k() -> None:
    assert hit_at_k(1, 1)
    assert hit_at_k(2, 3)
    assert not hit_at_k(4, 3)
    assert not hit_at_k(None, 5)


def test_reciprocal_rank() -> None:
    assert reciprocal_rank(1) == 1.0
    assert reciprocal_rank(2) == 0.5
    assert reciprocal_rank(None) == 0.0