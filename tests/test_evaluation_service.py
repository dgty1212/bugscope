import pytest

from app.services.evaluation_service import (
    calculate_metrics,
    file_matches_expected,
    normalize_file_path,
)


def test_normalize_windows_path() -> None:
    result = normalize_file_path(
        r"src\main\java\UserService.java"
    )

    assert result == (
        "src/main/java/userservice.java"
    )


def test_full_path_match() -> None:
    assert file_matches_expected(
        actual_file=(
            "src/main/java/com/example/"
            "UserService.java"
        ),
        expected_file=(
            "src/main/java/com/example/"
            "UserService.java"
        ),
    )


def test_filename_only_match() -> None:
    assert file_matches_expected(
        actual_file=(
            "src/main/java/com/example/"
            "UserService.java"
        ),
        expected_file="UserService.java",
    )


def test_different_file_does_not_match() -> None:
    assert not file_matches_expected(
        actual_file="src/UserRepository.java",
        expected_file="UserService.java",
    )


def test_calculate_metrics() -> None:
    ranks = [
        1,
        2,
        4,
        None,
    ]

    metrics = calculate_metrics(ranks)

    assert metrics.top_1_accuracy == pytest.approx(
        25.0
    )

    assert metrics.top_3_accuracy == pytest.approx(
        50.0
    )

    assert metrics.top_5_accuracy == pytest.approx(
        75.0
    )