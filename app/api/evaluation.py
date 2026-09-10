from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.evaluation import (
    ComparativeRetrievalEvaluationResponse,
    ComparativeCaseEvaluationResponse,
    RetrievalModeMetricsResponse,
    RetrievalCaseResult,
    RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
    RetrievalMetrics,
    RetrievalModeMetricsResponse,
    StructuralUsageMetricsResponse,
)
from app.services import (
    evaluation_service,
    project_service,
)
from app.services.embedding_service import (
    EmbeddingGenerationError,
)
from app.services.evaluation_service import (
    NoEvaluationCasesError,
)
from app.services.retrieval_service import (
    NoEmbeddedChunksError,
)

router = APIRouter(
    prefix="/projects/{project_id}/evaluations",
    tags=["evaluation"],
)

DbSession = Annotated[
    Session,
    Depends(get_db),
]


def validate_project_exists(
    db: Session,
    project_id: int,
) -> None:
    project = project_service.get_project(
        db=db,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )


@router.post(
    "/retrieval",
    response_model=RetrievalEvaluationResponse,
)
def evaluate_project_retrieval(
    project_id: int,
    request: RetrievalEvaluationRequest,
    db: DbSession,
) -> RetrievalEvaluationResponse:
    """Vector와 Hybrid 검색 성능을 비교한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    try:
        result = evaluation_service.evaluate_retrieval(
            db=db,
            project_id=project_id,
            limit=request.limit,
        )

    except NoEvaluationCasesError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "평가 가능한 DebugCase가 없습니다. "
                "resolved=true이고 expected_file이 "
                "등록된 사례가 필요합니다."
            ),
        ) from error

    except NoEmbeddedChunksError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "검색 가능한 코드 임베딩이 없습니다."
            ),
        ) from error

    except EmbeddingGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "평가 중 검색 임베딩 생성에 실패했습니다."
            ),
        ) from error

    return RetrievalEvaluationResponse(
        project_id=project_id,
        ground_truth_cases=result.ground_truth_cases,
        evaluated_cases=result.evaluated_cases,
        skipped_cases=result.skipped_cases,
        vector=RetrievalMetrics(
            top_1_accuracy=(
                result.vector_metrics.top_1_accuracy
            ),
            top_3_accuracy=(
                result.vector_metrics.top_3_accuracy
            ),
            top_5_accuracy=(
                result.vector_metrics.top_5_accuracy
            ),
        ),
        hybrid=RetrievalMetrics(
            top_1_accuracy=(
                result.hybrid_metrics.top_1_accuracy
            ),
            top_3_accuracy=(
                result.hybrid_metrics.top_3_accuracy
            ),
            top_5_accuracy=(
                result.hybrid_metrics.top_5_accuracy
            ),
        ),
        cases=[
            RetrievalCaseResult(
                debug_case_id=case.debug_case_id,
                expected_file=case.expected_file,
                vector_rank=case.vector_rank,
                hybrid_rank=case.hybrid_rank,
            )
            for case in result.cases
        ],
    )
    
def build_metrics_response(
    metrics: evaluation_service.RetrievalModeMetrics,
) -> RetrievalModeMetricsResponse:
    return RetrievalModeMetricsResponse(
        evaluated_cases=metrics.evaluated_cases,
        symbol_cases=metrics.symbol_cases,
        file_top1=metrics.file_top1,
        file_top3=metrics.file_top3,
        file_top5=metrics.file_top5,
        file_mrr=metrics.file_mrr,
        symbol_top1=metrics.symbol_top1,
        symbol_top3=metrics.symbol_top3,
        symbol_top5=metrics.symbol_top5,
        symbol_mrr=metrics.symbol_mrr,
        average_context_count=metrics.average_context_count,
    )
def build_structural_usage_response(
    usage: evaluation_service.StructuralUsageMetrics,
) -> StructuralUsageMetricsResponse:
    return StructuralUsageMetricsResponse(
        total_cases=usage.total_cases,
        trace_cases=usage.trace_cases,
        caller_cases=usage.caller_cases,
        callee_cases=usage.callee_cases,
        semantic_only_cases=usage.semantic_only_cases,
        trace_rate=usage.trace_rate,
        caller_rate=usage.caller_rate,
        callee_rate=usage.callee_rate,
        semantic_only_rate=usage.semantic_only_rate,
    )

@router.post(
    "/retrieval/compare",
    response_model=ComparativeRetrievalEvaluationResponse,
)
def compare_retrieval_modes(
    project_id: int,
    db: DbSession,
) -> ComparativeRetrievalEvaluationResponse:
    result = (
        evaluation_service
        .evaluate_project_retrieval_modes(
            db=db,
            project_id=project_id,
            top_k=5,
        )
    )

    return ComparativeRetrievalEvaluationResponse(
        project_id=result.project_id,
        evaluated_cases=result.evaluated_cases,
        vector=build_metrics_response(
            result.vector
        ),
        hybrid=build_metrics_response(
            result.hybrid
        ),
        structural=build_metrics_response(
            result.structural
        ),
        structural_usage=build_structural_usage_response(
            result.structural_usage
        ),
        cases=[
            ComparativeCaseEvaluationResponse(
                debug_case_id=case.debug_case_id,
                expected_file=case.expected_file,
                expected_symbol=case.expected_symbol,
                vector_file_rank=case.vector_file_rank,
                hybrid_file_rank=case.hybrid_file_rank,
                structural_file_rank=(
                    case.structural_file_rank
                ),
                vector_symbol_rank=(
                    case.vector_symbol_rank
                ),
                hybrid_symbol_rank=(
                    case.hybrid_symbol_rank
                ),
                structural_symbol_rank=(
                    case.structural_symbol_rank
                ),
                structural_context_types=(
                    case.structural_context_types
                ),
                structural_context_details=(
                    case.structural_context_details
                ),
            )
            for case in result.cases
        ],
    )