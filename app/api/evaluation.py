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
    RetrievalCaseResult,
    RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
    RetrievalMetrics,
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