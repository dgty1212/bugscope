from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.debug_case import DebugCase
from app.services import retrieval_service
from app.services.analysis_service import build_retrieval_query
from app.services.retrieval_service import SearchHit

TOP_K_VALUES = (1, 3, 5)

CANDIDATE_K = 25


class NoEvaluationCasesError(Exception):
    """평가 가능한 DebugCase가 없음."""


@dataclass(frozen=True, slots=True)
class CaseEvaluation:
    """개별 사례 평가 결과."""

    debug_case_id: int
    expected_file: str

    vector_rank: int | None
    hybrid_rank: int | None


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """검색 성능 지표."""

    top_1_accuracy: float
    top_3_accuracy: float
    top_5_accuracy: float


@dataclass(frozen=True, slots=True)
class RetrievalEvaluation:
    """전체 검색 평가 결과."""

    ground_truth_cases: int
    evaluated_cases: int
    skipped_cases: int

    vector_metrics: EvaluationMetrics
    hybrid_metrics: EvaluationMetrics

    cases: list[CaseEvaluation]


def normalize_file_path(
    file_path: str,
) -> str:
    """OS에 관계없이 파일 경로를 비교할 수 있도록 정규화한다."""

    normalized = (
        file_path
        .strip()
        .replace("\\", "/")
        .lower()
    )

    while normalized.startswith("./"):
        normalized = normalized[2:]

    return normalized


def file_matches_expected(
    actual_file: str,
    expected_file: str,
) -> bool:
    """검색 결과 파일이 정답 파일인지 확인한다."""

    actual = normalize_file_path(actual_file)
    expected = normalize_file_path(expected_file)

    if not expected:
        return False

    # expected_file에 전체 경로가 저장되어 있다면
    # 전체 경로 기준으로 비교한다.
    if "/" in expected:
        return actual == expected

    # UserService.java처럼 파일명만 저장한 경우
    # basename으로 비교한다.
    actual_name = actual.rsplit("/", 1)[-1]

    return actual_name == expected


def find_file_rank(
    hits: list[SearchHit],
    expected_file: str,
) -> int | None:
    """정답 파일이 검색 결과 몇 위인지 반환한다."""

    for rank, hit in enumerate(
        hits,
        start=1,
    ):
        if file_matches_expected(
            actual_file=hit.code_chunk.file_path,
            expected_file=expected_file,
        ):
            return rank

    return None


def calculate_metrics(
    ranks: list[int | None],
) -> EvaluationMetrics:
    """검색 순위 목록에서 Top-K 정확도를 계산한다."""

    if not ranks:
        return EvaluationMetrics(
            top_1_accuracy=0.0,
            top_3_accuracy=0.0,
            top_5_accuracy=0.0,
        )

    total = len(ranks)

    def accuracy_at(k: int) -> float:
        hits = sum(
            1
            for rank in ranks
            if rank is not None and rank <= k
        )

        return round(
            hits / total * 100,
            2,
        )

    return EvaluationMetrics(
        top_1_accuracy=accuracy_at(1),
        top_3_accuracy=accuracy_at(3),
        top_5_accuracy=accuracy_at(5),
    )


def evaluate_retrieval(
    db: Session,
    project_id: int,
    limit: int = 50,
) -> RetrievalEvaluation:
    """Vector와 Hybrid 검색 성능을 비교한다."""

    statement = (
        select(DebugCase)
        .where(
            DebugCase.project_id == project_id,
            DebugCase.resolved.is_(True),
            DebugCase.expected_file.is_not(None),
        )
        .order_by(DebugCase.id)
        .limit(limit)
    )

    debug_cases = list(
        db.scalars(statement).all()
    )

    if not debug_cases:
        raise NoEvaluationCasesError

    case_results: list[CaseEvaluation] = []

    vector_ranks: list[int | None] = []
    hybrid_ranks: list[int | None] = []

    skipped_cases = 0

    for debug_case in debug_cases:
        expected_file = (
            debug_case.expected_file or ""
        ).strip()

        if not expected_file:
            skipped_cases += 1
            continue

        retrieval_query = build_retrieval_query(
            error_log=debug_case.error_log,
            situation=debug_case.situation,
        )

        # Embedding 호출은 여기서 딱 한 번 발생한다.
        vector_candidates = (
            retrieval_service.search_code_chunks(
                db=db,
                project_id=project_id,
                query=retrieval_query,
                top_k=CANDIDATE_K,
            )
        )

        # 동일한 후보를 Hybrid 점수로 다시 정렬한다.
        hybrid_candidates = (
            retrieval_service.rerank_search_hits_hybrid(
                query=retrieval_query,
                candidates=vector_candidates,
                top_k=CANDIDATE_K,
            )
        )

        vector_rank = find_file_rank(
            hits=vector_candidates,
            expected_file=expected_file,
        )

        hybrid_rank = find_file_rank(
            hits=hybrid_candidates,
            expected_file=expected_file,
        )

        vector_ranks.append(vector_rank)
        hybrid_ranks.append(hybrid_rank)

        case_results.append(
            CaseEvaluation(
                debug_case_id=debug_case.id,
                expected_file=expected_file,
                vector_rank=vector_rank,
                hybrid_rank=hybrid_rank,
            )
        )

    if not case_results:
        raise NoEvaluationCasesError

    return RetrievalEvaluation(
        ground_truth_cases=len(debug_cases),
        evaluated_cases=len(case_results),
        skipped_cases=skipped_cases,
        vector_metrics=calculate_metrics(
            vector_ranks
        ),
        hybrid_metrics=calculate_metrics(
            hybrid_ranks
        ),
        cases=case_results,
    )