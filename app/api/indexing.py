from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.code_chunk import (
    CodeChunkResponse,
    ProjectIndexRequest,
    ProjectIndexResponse,
)
from app.services import indexing_service, project_service
from app.services.indexing_service import (
    NoSourceFilesError,
    ProjectIndexingError,
)

router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["indexing"],
)

DbSession = Annotated[Session, Depends(get_db)]


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


@router.post(
    "/index",
    response_model=ProjectIndexResponse,
)
def index_project(
    project_id: int,
    request: ProjectIndexRequest,
    db: DbSession,
) -> ProjectIndexResponse:
    """프로젝트의 소스 파일을 코드 조각으로 인덱싱한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    try:
        result = indexing_service.index_project(
            db=db,
            project_id=project_id,
            max_lines=request.max_lines,
            overlap_lines=request.overlap_lines,
        )

    except NoSourceFilesError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="인덱싱할 소스 파일이 없습니다.",
        ) from error

    except ProjectIndexingError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="소스코드 인덱싱 중 오류가 발생했습니다.",
        ) from error

    return ProjectIndexResponse(
        project_id=project_id,
        indexed_files=result.indexed_files,
        created_chunks=result.created_chunks,
        max_lines=request.max_lines,
        overlap_lines=request.overlap_lines,
    )


@router.get(
    "/chunks",
    response_model=list[CodeChunkResponse],
)
def get_code_chunks(
    project_id: int,
    db: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[CodeChunkResponse]:
    """프로젝트의 코드 조각 목록을 조회한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    return indexing_service.get_code_chunks(
        db=db,
        project_id=project_id,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/chunks/{chunk_id}",
    response_model=CodeChunkResponse,
)
def get_code_chunk(
    project_id: int,
    chunk_id: int,
    db: DbSession,
) -> CodeChunkResponse:
    """코드 조각 하나를 조회한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    code_chunk = indexing_service.get_code_chunk(
        db=db,
        project_id=project_id,
        chunk_id=chunk_id,
    )

    if code_chunk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="코드 조각을 찾을 수 없습니다.",
        )

    return code_chunk