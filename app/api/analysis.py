from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analysis import (
    AnalysisContext,
    DebugAnalysisRequest,
    DebugAnalysisResponse,
)
from app.services import (
    analysis_service,
    debug_case_service,
    project_service,
)
from app.services.context_selector import SelectedContext
from app.services.debug_case_service import DebugCaseSaveError
from app.services.embedding_service import (
    EmbeddingGenerationError,
)
from app.services.llm_service import LLMAnalysisError
from app.services.retrieval_service import (
    NoEmbeddedChunksError,
)

router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["analysis"],
)

DbSession = Annotated[
    Session,
    Depends(get_db),
]


def validate_project_exists(
    db: Session,
    project_id: int,
) -> None:
    """프로젝트 존재 여부를 확인한다."""

    project = project_service.get_project(
        db=db,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )


def build_analysis_contexts(
    contexts: list[SelectedContext],
) -> list[AnalysisContext]:
    """SelectedContext를 API 응답 Schema로 변환한다."""

    return [
        AnalysisContext(
            context_id=context_id,
            context_type=context.context_type,
            source_type=context.source_type,
            source_id=context.source_id,
            file_path=context.file_path,
            class_name=context.class_name,
            symbol_name=context.symbol_name,
            start_line=context.start_line,
            end_line=context.end_line,
            score=context.score,
        )
        for context_id, context in enumerate(
            contexts,
            start=1,
        )
    ]


def serialize_contexts(
    contexts: list[SelectedContext],
) -> list[dict]:
    """DebugCase JSONB 저장용 Context 데이터."""

    return [
        {
            "context_id": context_id,
            "context_type": context.context_type,
            "source_type": context.source_type,
            "source_id": context.source_id,
            "file_path": context.file_path,
            "class_name": context.class_name,
            "symbol_name": context.symbol_name,
            "start_line": context.start_line,
            "end_line": context.end_line,
            "score": context.score,
        }
        for context_id, context in enumerate(
            contexts,
            start=1,
        )
    ]


@router.post(
    "/analyze",
    response_model=DebugAnalysisResponse,
)
def analyze_project_error(
    project_id: int,
    request: DebugAnalysisRequest,
    db: DbSession,
) -> DebugAnalysisResponse:
    """오류 로그와 소스코드를 기반으로 원인을 분석한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    try:
        result = analysis_service.analyze_debug_case(
            db=db,
            project_id=project_id,
            error_log=request.error_log,
            situation=request.situation,
            top_k=request.top_k,
            retrieval_mode=request.retrieval_mode,
        )

    except NoEmbeddedChunksError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "검색 가능한 코드 임베딩이 없습니다. "
                "먼저 인덱싱과 임베딩 생성을 실행하세요."
            ),
        ) from error

    except EmbeddingGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="검색 질의 임베딩 생성에 실패했습니다.",
        ) from error

    except LLMAnalysisError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM 오류 분석에 실패했습니다.",
        ) from error

    analysis_contexts = build_analysis_contexts(
        result.contexts,
    )

    stored_contexts = serialize_contexts(
        result.contexts,
    )

    try:
        debug_case = debug_case_service.create_debug_case(
            db=db,
            project_id=project_id,
            error_log=request.error_log,
            situation=request.situation,
            retrieval_query=result.retrieval_query,

            # DB 컬럼 이름은 아직 retrieved_chunks이지만,
            # 내부에는 이제 selected context metadata를 저장한다.
            retrieved_chunks=stored_contexts,

            analysis_result=result.analysis.model_dump(),
        )

    except DebugCaseSaveError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 결과 저장에 실패했습니다.",
        ) from error

    return DebugAnalysisResponse(
        debug_case_id=debug_case.id,
        project_id=project_id,
        retrieval_mode=request.retrieval_mode,
        retrieval_query=result.retrieval_query,
        contexts=analysis_contexts,
        analysis=result.analysis,
    )