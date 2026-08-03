from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class DuplicateProjectNameError(Exception):
    """동일한 프로젝트 이름이 존재할 때 발생."""



def create_project(
    db: Session,
    project_data: ProjectCreate,
) -> Project:
    """새 프로젝트를 생성한다."""

    project = Project(
        name=project_data.name,
        description=project_data.description,
        language=project_data.language,
    )

    db.add(project)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise DuplicateProjectNameError from error

    db.refresh(project)

    return project


def get_projects(
    db: Session,
    offset: int = 0,
    limit: int = 20,
) -> list[Project]:
    """프로젝트 목록을 조회한다."""

    statement = (
        select(Project)
        .order_by(Project.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def get_project(
    db: Session,
    project_id: int,
) -> Project | None:
    """ID로 프로젝트 하나를 조회한다."""

    return db.get(Project, project_id)


def update_project(
    db: Session,
    project: Project,
    project_data: ProjectUpdate,
) -> Project:
    """프로젝트 정보를 수정한다."""

    update_data = project_data.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(project, field_name, value)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise DuplicateProjectNameError from error

    db.refresh(project)

    return project


def delete_project(
    db: Session,
    project: Project,
) -> None:
    """프로젝트를 삭제한다."""

    db.delete(project)
    db.commit()