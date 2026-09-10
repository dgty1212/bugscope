from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.analysis_service import (
    build_retrieval_query,
)
from app.services.context_selector import (
    SelectedContext,
    select_debug_context,
)


@dataclass(frozen=True, slots=True)
class StructuralRetrievalResult:
    contexts: list[SelectedContext]

    file_rank: int | None
    symbol_rank: int | None


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lower()


def file_matches(
    context: SelectedContext,
    expected_file: str,
) -> bool:
    context_path = normalize_path(
        context.file_path
    )
    expected_path = normalize_path(
        expected_file
    )

    return (
        context_path == expected_path
        or context_path.endswith(
            (
                f"/{expected_path}",
                expected_path,
            )
        )
    )

def symbol_matches(
    context: SelectedContext,
    expected_symbol: str,
) -> bool:
    expected = expected_symbol.strip()

    if not expected:
        return False

    # Structural Symbol
    if (
        context.symbol_name
        and context.symbol_name == expected
    ):
        return True

    # Vector / Semantic Chunk에서는
    # 코드 내부에 Symbol 이름이 포함되어 있는지 확인한다.
    return expected in context.content


def find_rank(
    contexts: list[SelectedContext],
    matcher,
) -> int | None:
    for rank, context in enumerate(
        contexts,
        start=1,
    ):
        if matcher(context):
            return rank

    return None


def evaluate_structural_case(
    db: Session,
    project_id: int,
    error_log: str,
    situation: str | None,
    expected_file: str,
    expected_symbol: str | None,
    top_k: int = 8,
) -> StructuralRetrievalResult:
    retrieval_query = build_retrieval_query(
        error_log=error_log,
        situation=situation,
    )

    contexts = select_debug_context(
        db=db,
        project_id=project_id,
        error_log=error_log,
        retrieval_query=retrieval_query,
        max_contexts=top_k,
    )

    file_rank = find_rank(
        contexts,
        lambda context: file_matches(
            context,
            expected_file,
        ),
    )

    symbol_rank: int | None = None

    if expected_symbol:
        symbol_rank = find_rank(
            contexts,
            lambda context: (
                file_matches(
                    context,
                    expected_file,
                )
                and symbol_matches(
                    context,
                    expected_symbol,
                )
            ),
        )

    return StructuralRetrievalResult(
        contexts=contexts,
        file_rank=file_rank,
        symbol_rank=symbol_rank,
    )
    
def hit_at_k(
    rank: int | None,
    k: int,
) -> bool:
    return (
        rank is not None
        and rank <= k
    )


def reciprocal_rank(
    rank: int | None,
) -> float:
    if rank is None:
        return 0.0

    return 1.0 / rank