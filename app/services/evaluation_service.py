from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.debug_case import DebugCase
from app.services import retrieval_service
from app.services.analysis_service import build_retrieval_query
from app.services.context_selector import (
    SelectedContext,
    search_hits_to_contexts,
    select_debug_context,
)
from app.services.retrieval_service import SearchHit
from app.services.structural_evaluation_service import (
    file_matches,
    find_rank,
    hit_at_k,
    reciprocal_rank,
    symbol_matches,
)

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
@dataclass(frozen=True, slots=True)
class RetrievalModeMetrics:
    """하나의 Retrieval 방식에 대한 평가 결과."""

    evaluated_cases: int
    symbol_cases: int

    file_top1: float
    file_top3: float
    file_top5: float
    file_mrr: float

    symbol_top1: float | None
    symbol_top3: float | None
    symbol_top5: float | None
    symbol_mrr: float | None

    average_context_count: float


@dataclass(frozen=True, slots=True)
class ComparativeCaseEvaluation:
    debug_case_id: int

    expected_file: str
    expected_symbol: str | None

    vector_file_rank: int | None
    hybrid_file_rank: int | None
    structural_file_rank: int | None

    vector_symbol_rank: int | None
    hybrid_symbol_rank: int | None
    structural_symbol_rank: int | None


@dataclass(frozen=True, slots=True)
class ComparativeRetrievalEvaluation:
    project_id: int
    evaluated_cases: int

    vector: RetrievalModeMetrics
    hybrid: RetrievalModeMetrics
    structural: RetrievalModeMetrics

    cases: list[ComparativeCaseEvaluation]

@dataclass(frozen=True, slots=True)
class CaseRetrievalEvaluation:
    file_rank: int | None
    symbol_rank: int | None

    has_expected_symbol: bool

    context_count: int

def evaluate_contexts(
    contexts: list[SelectedContext],
    expected_file: str,
    expected_symbol: str | None,
) -> CaseRetrievalEvaluation:
    """선별된 Context에서 정답 파일/심볼의 순위를 계산한다."""

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

    return CaseRetrievalEvaluation(
        file_rank=file_rank,
        symbol_rank=symbol_rank,
        has_expected_symbol=bool(expected_symbol),
        context_count=len(contexts),
    )
    
def retrieve_evaluation_contexts(
    db: Session,
    debug_case: DebugCase,
    retrieval_mode: str,
    top_k: int,
) -> list[SelectedContext]:
    """평가용 Retrieval Context를 생성한다."""

    retrieval_query = build_retrieval_query(
        error_log=debug_case.error_log,
        situation=debug_case.situation,
    )

    if retrieval_mode == "vector":
        hits = retrieval_service.search_code_chunks(
            db=db,
            project_id=debug_case.project_id,
            query=retrieval_query,
            top_k=top_k,
        )

        return search_hits_to_contexts(
            hits,
        )

    if retrieval_mode == "hybrid":
        hits = retrieval_service.search_code_chunks_hybrid(
            db=db,
            project_id=debug_case.project_id,
            query=retrieval_query,
            top_k=top_k,
        )

        return search_hits_to_contexts(
            hits,
        )

    if retrieval_mode == "structural":
        return select_debug_context(
            db=db,
            project_id=debug_case.project_id,
            error_log=debug_case.error_log,
            retrieval_query=retrieval_query,
            max_contexts=top_k,
        )

    raise ValueError(
        f"지원하지 않는 retrieval_mode입니다: "
        f"{retrieval_mode}"
    )

def calculate_mode_metrics(
    results: list[CaseRetrievalEvaluation],
) -> RetrievalModeMetrics:
    """여러 Debug Case 결과를 하나의 Metric으로 집계한다."""

    case_count = len(results)

    if case_count == 0:
        return RetrievalModeMetrics(
            evaluated_cases=0,
            symbol_cases=0,
            file_top1=0.0,
            file_top3=0.0,
            file_top5=0.0,
            file_mrr=0.0,
            symbol_top1=None,
            symbol_top3=None,
            symbol_top5=None,
            symbol_mrr=None,
            average_context_count=0.0,
        )

    file_top1 = sum(
        hit_at_k(result.file_rank, 1)
        for result in results
    ) / case_count

    file_top3 = sum(
        hit_at_k(result.file_rank, 3)
        for result in results
    ) / case_count

    file_top5 = sum(
        hit_at_k(result.file_rank, 5)
        for result in results
    ) / case_count

    file_mrr = sum(
        reciprocal_rank(result.file_rank)
        for result in results
    ) / case_count

    average_context_count = sum(
        result.context_count
        for result in results
    ) / case_count

    # expected_symbol이 존재하는 Case만
    # Symbol 평가 대상에 포함한다.
    symbol_results = [
        result
        for result in results
        if result.has_expected_symbol
    ]

    symbol_case_count = len(symbol_results)

    if symbol_case_count == 0:
        symbol_top1 = None
        symbol_top3 = None
        symbol_top5 = None
        symbol_mrr = None

    else:
        symbol_top1 = sum(
            hit_at_k(result.symbol_rank, 1)
            for result in symbol_results
        ) / symbol_case_count

        symbol_top3 = sum(
            hit_at_k(result.symbol_rank, 3)
            for result in symbol_results
        ) / symbol_case_count

        symbol_top5 = sum(
            hit_at_k(result.symbol_rank, 5)
            for result in symbol_results
        ) / symbol_case_count

        symbol_mrr = sum(
            reciprocal_rank(result.symbol_rank)
            for result in symbol_results
        ) / symbol_case_count

    return RetrievalModeMetrics(
        evaluated_cases=case_count,
        symbol_cases=symbol_case_count,
        file_top1=file_top1,
        file_top3=file_top3,
        file_top5=file_top5,
        file_mrr=file_mrr,
        symbol_top1=symbol_top1,
        symbol_top3=symbol_top3,
        symbol_top5=symbol_top5,
        symbol_mrr=symbol_mrr,
        average_context_count=average_context_count,
    )
    
def evaluate_project_retrieval_modes(
    db: Session,
    project_id: int,
    top_k: int = 5,
) -> ComparativeRetrievalEvaluation:
    """
    Ground Truth가 등록된 DebugCase를 이용해
    Vector / Hybrid / Structural Retrieval을 비교한다.
    """

    statement = (
        select(DebugCase)
        .where(
            DebugCase.project_id == project_id,
            DebugCase.resolved.is_(True),
            DebugCase.expected_file.is_not(None),
        )
        .order_by(DebugCase.id)
    )

    debug_cases = list(
        db.scalars(statement).all()
    )

    vector_results: list[
        CaseRetrievalEvaluation
    ] = []

    hybrid_results: list[
        CaseRetrievalEvaluation
    ] = []

    structural_results: list[
        CaseRetrievalEvaluation
    ] = []
    
    comparative_cases: list[
        ComparativeCaseEvaluation
    ] = []

    for debug_case in debug_cases:
        expected_file = debug_case.expected_file

        if not expected_file:
            continue

        expected_symbol = (
            debug_case.expected_symbol
        )

        # ----------------------------
        # Vector
        # ----------------------------
        vector_contexts = (
            retrieve_evaluation_contexts(
                db=db,
                debug_case=debug_case,
                retrieval_mode="vector",
                top_k=top_k,
            )
        )

        vector_result = evaluate_contexts(
            contexts=vector_contexts,
            expected_file=expected_file,
            expected_symbol=expected_symbol,
        )


        # ----------------------------
        # Hybrid
        # ----------------------------
        hybrid_contexts = (
            retrieve_evaluation_contexts(
                db=db,
                debug_case=debug_case,
                retrieval_mode="hybrid",
                top_k=top_k,
            )
        )

        hybrid_result = evaluate_contexts(
            contexts=hybrid_contexts,
            expected_file=expected_file,
            expected_symbol=expected_symbol,
        )

        # ----------------------------
        # Structural
        # ----------------------------
        structural_contexts = (
            retrieve_evaluation_contexts(
                db=db,
                debug_case=debug_case,
                retrieval_mode="structural",
                top_k=top_k,
            )
        )

        structural_result = evaluate_contexts(
            contexts=structural_contexts,
            expected_file=expected_file,
            expected_symbol=expected_symbol,
        )
        
        vector_results.append(
            vector_result
        )

        hybrid_results.append(
            hybrid_result
        )

        structural_results.append(
            structural_result
        )
        
        comparative_cases.append(
            ComparativeCaseEvaluation(
                debug_case_id=debug_case.id,
                expected_file=expected_file,
                expected_symbol=expected_symbol,
                vector_file_rank=(
                    vector_result.file_rank
                ),
                hybrid_file_rank=(
                    hybrid_result.file_rank
                ),
                structural_file_rank=(
                    structural_result.file_rank
                ),
                vector_symbol_rank=(
                    vector_result.symbol_rank
                ),
                hybrid_symbol_rank=(
                    hybrid_result.symbol_rank
                ),
                structural_symbol_rank=(
                    structural_result.symbol_rank
                ),
            )
        )

    return ComparativeRetrievalEvaluation(
        project_id=project_id,
        evaluated_cases=len(vector_results),
        vector=calculate_mode_metrics(
            vector_results
        ),
        hybrid=calculate_mode_metrics(
            hybrid_results
        ),
        structural=calculate_mode_metrics(
            structural_results
        ),
        cases=comparative_cases,
    )