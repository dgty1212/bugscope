from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.debug_case import (
    DebugCaseDetail,
    DebugCaseSummary,
    DebugCaseUpdate,
)
from app.services import (
    debug_case_service,
    project_service,
)

router = APIRouter(
    prefix="/projects/{project_id}/debug-cases",
    tags=["debug-cases"],
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


@router.get(
    "",
    response_model=list[DebugCaseSummary],
)
def get_debug_cases(
    project_id: int,
    db: DbSession,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 50,
) -> list[DebugCaseSummary]:
    """디버깅 사례 목록."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    return debug_case_service.get_debug_cases(
        db=db,
        project_id=project_id,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{debug_case_id}",
    response_model=DebugCaseDetail,
)
def get_debug_case(
    project_id: int,
    debug_case_id: int,
    db: DbSession,
) -> DebugCaseDetail:
    """디버깅 사례 상세 조회."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    debug_case = debug_case_service.get_debug_case(
        db=db,
        project_id=project_id,
        debug_case_id=debug_case_id,
    )

    if debug_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="디버깅 사례를 찾을 수 없습니다.",
        )

    return debug_case


@router.patch(
    "/{debug_case_id}",
    response_model=DebugCaseDetail,
)
def update_debug_case(
    project_id: int,
    debug_case_id: int,
    update_data: DebugCaseUpdate,
    db: DbSession,
) -> DebugCaseDetail:
    """실제 원인 및 정답 정보를 기록한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    debug_case = debug_case_service.get_debug_case(
        db=db,
        project_id=project_id,
        debug_case_id=debug_case_id,
    )

    if debug_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="디버깅 사례를 찾을 수 없습니다.",
        )

    return debug_case_service.update_debug_case(
        db=db,
        debug_case=debug_case,
        update_data=update_data,
    )


@router.delete(
    "/{debug_case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_debug_case(
    project_id: int,
    debug_case_id: int,
    db: DbSession,
) -> Response:
    """디버깅 사례를 삭제한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    debug_case = debug_case_service.get_debug_case(
        db=db,
        project_id=project_id,
        debug_case_id=debug_case_id,
    )

    if debug_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="디버깅 사례를 찾을 수 없습니다.",
        )

    debug_case_service.delete_debug_case(
        db=db,
        debug_case=debug_case,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )