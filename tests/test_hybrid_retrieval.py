import pytest

from app.services.hybrid_retrieval import (
    calculate_hybrid_score,
    calculate_lexical_scores,
    extract_query_signals,
    normalize_cosine_similarity,
)


def test_extract_stack_trace_signals() -> None:
    """Java stack trace에서 파일명과 식별자를 추출할 수 있어야 한다."""

    query = (
        "java.lang.NullPointerException\n"
        "at com.example.UserService.getUserName"
        "(UserService.java:21)"
    )

    signals = extract_query_signals(query)

    assert "userservice.java" in signals.file_names

    assert "userservice" in signals.identifiers
    assert "getusername" in signals.identifiers
    assert "nullpointerexception" in signals.identifiers


def test_extract_multiple_java_files() -> None:
    """오류 로그에 여러 Java 파일이 있으면 모두 추출해야 한다."""

    query = (
        "at UserService.getUserName(UserService.java:21)\n"
        "at UserController.findUser(UserController.java:42)"
    )

    signals = extract_query_signals(query)

    assert "userservice.java" in signals.file_names
    assert "usercontroller.java" in signals.file_names

    assert "getusername" in signals.identifiers
    assert "finduser" in signals.identifiers


def test_filename_exact_match() -> None:
    """오류 로그의 파일명이 파일 경로와 일치하면 최대 점수를 줘야 한다."""

    signals = extract_query_signals(
        "at UserService.getUserName"
        "(UserService.java:21)"
    )

    scores = calculate_lexical_scores(
        signals=signals,
        file_path=(
            "src/main/java/"
            "com/example/UserService.java"
        ),
        content="""
        public String getUserName(Long id) {
            return userName.toUpperCase();
        }
        """,
    )

    assert scores.filename_score == pytest.approx(1.0)
    assert scores.keyword_score > 0.0


def test_filename_non_match() -> None:
    """전혀 다른 파일은 파일명 점수를 받지 않아야 한다."""

    signals = extract_query_signals(
        "UserService.java"
    )

    scores = calculate_lexical_scores(
        signals=signals,
        file_path="src/main/java/UserRepository.java",
        content="public class UserRepository {}",
    )

    assert scores.filename_score == pytest.approx(0.0)


def test_keyword_score_is_based_on_match_ratio() -> None:
    """식별자 중 일부만 일치하면 부분 점수를 받아야 한다."""

    query = (
        "UserService.java "
        "UserService getUserName"
    )

    signals = extract_query_signals(query)

    scores = calculate_lexical_scores(
        signals=signals,
        file_path="src/UserService.java",
        content="public class UserService {}",
    )

    assert 0.0 <= scores.keyword_score <= 1.0


@pytest.mark.parametrize(
    ("similarity", "expected"),
    [
        (-1.0, 0.0),
        (0.0, 0.5),
        (1.0, 1.0),
    ],
)
def test_normalize_cosine_similarity(
    similarity: float,
    expected: float,
) -> None:
    """cosine similarity를 0~1 범위로 변환해야 한다."""

    result = normalize_cosine_similarity(
        similarity
    )

    assert result == pytest.approx(expected)


def test_normalize_cosine_similarity_is_clamped() -> None:
    """예상 범위를 벗어난 값도 0~1 사이로 제한해야 한다."""

    assert normalize_cosine_similarity(2.0) == pytest.approx(
        1.0
    )

    assert normalize_cosine_similarity(-2.0) == pytest.approx(
        0.0
    )


def test_hybrid_score_calculation() -> None:
    """현재 정의된 가중치 공식대로 점수가 계산되어야 한다."""

    score = calculate_hybrid_score(
        vector_similarity=1.0,
        filename_score=1.0,
        keyword_score=1.0,
    )

    assert score == pytest.approx(1.0)


def test_hybrid_score_without_lexical_match() -> None:
    """명시적 단서가 없으면 벡터 점수만 반영되어야 한다."""

    score = calculate_hybrid_score(
        vector_similarity=1.0,
        filename_score=0.0,
        keyword_score=0.0,
    )

    # vector weight = 0.60
    assert score == pytest.approx(0.60)