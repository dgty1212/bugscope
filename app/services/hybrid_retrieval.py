import re
from dataclasses import dataclass

JAVA_FILE_PATTERN = re.compile(
    r"\b([A-Za-z_$][A-Za-z0-9_$]*\.java)\b"
)

STACK_METHOD_PATTERN = re.compile(
    r"\bat\s+[\w.$]+\.([A-Za-z_$][A-Za-z0-9_$]*)"
    r"\(([A-Za-z_$][A-Za-z0-9_$]*\.java)(?::\d+)?\)"
)

IDENTIFIER_PATTERN = re.compile(
    r"\b[A-Za-z_$][A-Za-z0-9_$]{2,}\b"
)


STOP_WORDS = {
    "java",
    "lang",
    "main",
    "string",
    "null",
    "true",
    "false",
    "void",
    "public",
    "private",
    "protected",
    "class",
    "return",
    "because",
    "cannot",
    "invoke",
    "error",
    "exception",
}


@dataclass(frozen=True, slots=True)
class QuerySignals:
    """오류 로그에서 추출한 명시적 검색 단서."""

    file_names: frozenset[str]
    identifiers: frozenset[str]


@dataclass(frozen=True, slots=True)
class LexicalScores:
    """키워드 기반 검색 점수."""

    filename_score: float
    keyword_score: float


def extract_query_signals(
    query: str,
) -> QuerySignals:
    """오류 로그에서 파일명과 Java 식별자를 추출한다."""

    file_names: set[str] = set()
    identifiers: set[str] = set()

    # UserService.java 형태
    for file_name in JAVA_FILE_PATTERN.findall(query):
        file_names.add(file_name.lower())

        class_name = file_name.removesuffix(".java")

        if class_name:
            identifiers.add(class_name.lower())

    # Java stack trace:
    # at ...UserService.getUserName(UserService.java:21)
    for method_name, file_name in STACK_METHOD_PATTERN.findall(
        query
    ):
        identifiers.add(method_name.lower())
        file_names.add(file_name.lower())

    # CamelCase, Exception 이름 등의 기술 식별자 추출
    for token in IDENTIFIER_PATTERN.findall(query):
        lowered = token.lower()

        if lowered in STOP_WORDS:
            continue

        is_technical_identifier = (
            any(character.isupper() for character in token[1:])
            or "_" in token
            or token.endswith(("Exception", "Error"))
        )

        if is_technical_identifier:
            identifiers.add(lowered)

    return QuerySignals(
        file_names=frozenset(file_names),
        identifiers=frozenset(identifiers),
    )


def calculate_lexical_scores(
    signals: QuerySignals,
    file_path: str,
    content: str,
) -> LexicalScores:
    """코드 조각이 오류 로그의 명시적 단서와 얼마나 일치하는지 계산한다."""

    normalized_path = file_path.lower()
    normalized_content = content.lower()

    # -------------------------
    # 파일명 점수
    # -------------------------

    filename_score = 0.0

    for file_name in signals.file_names:
        if file_name in normalized_path:
            filename_score = 1.0
            break

        class_name = file_name.removesuffix(".java")

        if class_name and class_name in normalized_path:
            filename_score = max(
                filename_score,
                0.8,
            )

    # -------------------------
    # 식별자 점수
    # -------------------------

    if not signals.identifiers:
        keyword_score = 0.0

    else:
        searchable_text = (
            normalized_path
            + "\n"
            + normalized_content
        )

        matched_identifiers = sum(
            1
            for identifier in signals.identifiers
            if identifier in searchable_text
        )

        keyword_score = (
            matched_identifiers
            / len(signals.identifiers)
        )

    return LexicalScores(
        filename_score=filename_score,
        keyword_score=keyword_score,
    )


def normalize_cosine_similarity(
    similarity: float,
) -> float:
    """-1~1 범위의 cosine similarity를 0~1로 변환한다."""

    normalized = (similarity + 1.0) / 2.0

    return max(
        0.0,
        min(1.0, normalized),
    )


def calculate_hybrid_score(
    vector_similarity: float,
    filename_score: float,
    keyword_score: float,
) -> float:
    """벡터와 명시적 코드 단서를 결합한다."""

    vector_score = normalize_cosine_similarity(
        vector_similarity
    )

    return (
        vector_score * 0.60
        + filename_score * 0.25
        + keyword_score * 0.15
    )