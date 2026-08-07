from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.retrieval import (
    CodeSearchRequest,
    CodeSearchResponse,
    CodeSearchResult,
    EmbeddingIndexRequest,
    EmbeddingIndexResponse,
)
from app.services import project_service, retrieval_service
from app.services.embedding_service import EmbeddingGenerationError
from app.services.retrieval_service import (
    NoCodeChunksError,
    NoEmbeddedChunksError,
    ProjectEmbeddingError,
)

router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["retrieval"],
)

DbSession = Annotated[Session, Depends(get_db)]

settings = get_settings()


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
    "/embeddings",
    response_model=EmbeddingIndexResponse,
)
def create_project_embeddings(
    project_id: int,
    request: EmbeddingIndexRequest,
    db: DbSession,
) -> EmbeddingIndexResponse:
    """코드 조각의 임베딩을 생성한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    try:
        result = retrieval_service.embed_project_chunks(
            db=db,
            project_id=project_id,
            force=request.force,
            batch_size=request.batch_size,
        )

    except NoCodeChunksError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "임베딩할 코드 조각이 없습니다. "
                "먼저 프로젝트 인덱싱을 실행하세요."
            ),
        ) from error

    except ProjectEmbeddingError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="코드 임베딩 생성에 실패했습니다.",
        ) from error

    return EmbeddingIndexResponse(
        project_id=project_id,
        total_chunks=result.total_chunks,
        embedded_chunks=result.embedded_chunks,
        skipped_chunks=result.skipped_chunks,
        model=settings.openai_embedding_model,
    )


@router.post(
    "/search",
    response_model=CodeSearchResponse,
)
def search_project_code(
    project_id: int,
    request: CodeSearchRequest,
    db: DbSession,
) -> CodeSearchResponse:
    """자연어 질의로 관련 코드 조각을 검색한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    try:
        hits = retrieval_service.search_code_chunks(
            db=db,
            project_id=project_id,
            query=request.query,
            top_k=request.top_k,
        )

    except NoEmbeddedChunksError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "검색 가능한 임베딩이 없습니다. "
                "먼저 임베딩 생성을 실행하세요."
            ),
        ) from error

    except EmbeddingGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="검색어 임베딩 생성에 실패했습니다.",
        ) from error

    results = [
        CodeSearchResult(
            chunk_id=hit.code_chunk.id,
            source_file_id=hit.code_chunk.source_file_id,
            file_path=hit.code_chunk.file_path,
            start_line=hit.code_chunk.start_line,
            end_line=hit.code_chunk.end_line,
            content=hit.code_chunk.content,
            distance=hit.distance,
            similarity=hit.similarity,
        )
        for hit in hits
    ]

    return CodeSearchResponse(
        project_id=project_id,
        query=request.query,
        results=results,
    )