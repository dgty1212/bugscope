from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services import project_service
from app.services.project_service import DuplicateProjectNameError

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    project_data: ProjectCreate,
    db: DbSession,
) -> ProjectResponse:
    """새 프로젝트를 등록한다."""

    try:
        return project_service.create_project(
            db=db,
            project_data=project_data,
        )

    except DuplicateProjectNameError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 이름의 프로젝트가 이미 존재합니다.",
        ) from error


@router.get(
    "",
    response_model=list[ProjectResponse],
)
def get_projects(
    db: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ProjectResponse]:
    """프로젝트 목록을 조회한다."""

    return project_service.get_projects(
        db=db,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
def get_project(
    project_id: int,
    db: DbSession,
) -> ProjectResponse:
    """특정 프로젝트를 조회한다."""

    project = project_service.get_project(
        db=db,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )

    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: DbSession,
) -> ProjectResponse:
    """프로젝트 정보를 수정한다."""

    project = project_service.get_project(
        db=db,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )

    try:
        return project_service.update_project(
            db=db,
            project=project,
            project_data=project_data,
        )

    except DuplicateProjectNameError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 이름의 프로젝트가 이미 존재합니다.",
        ) from error


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project(
    project_id: int,
    db: DbSession,
) -> None:
    """프로젝트를 삭제한다."""

    project = project_service.get_project(
        db=db,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )

    project_service.delete_project(
        db=db,
        project=project,
    )