from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.debug_case import DebugCase
from app.schemas.debug_case import DebugCaseUpdate


class DebugCaseSaveError(Exception):
    """디버깅 사례 저장 실패."""


def create_debug_case(
    db: Session,
    project_id: int,
    error_log: str,
    situation: str | None,
    retrieval_query: str,
    retrieved_chunks: list[dict[str, Any]],
    analysis_result: dict[str, Any],
) -> DebugCase:
    """분석 결과를 디버깅 사례로 저장한다."""

    debug_case = DebugCase(
        project_id=project_id,
        error_log=error_log,
        situation=situation,
        retrieval_query=retrieval_query,
        retrieved_chunks=retrieved_chunks,
        analysis_result=analysis_result,
    )

    db.add(debug_case)

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise DebugCaseSaveError from error

    db.refresh(debug_case)

    return debug_case


def get_debug_cases(
    db: Session,
    project_id: int,
    offset: int = 0,
    limit: int = 50,
) -> list[DebugCase]:
    """프로젝트의 디버깅 사례 목록을 조회한다."""

    statement = (
        select(DebugCase)
        .where(DebugCase.project_id == project_id)
        .order_by(DebugCase.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def get_debug_case(
    db: Session,
    project_id: int,
    debug_case_id: int,
) -> DebugCase | None:
    """디버깅 사례 하나를 조회한다."""

    statement = select(DebugCase).where(
        DebugCase.id == debug_case_id,
        DebugCase.project_id == project_id,
    )

    return db.scalar(statement)


def update_debug_case(
    db: Session,
    debug_case: DebugCase,
    update_data: DebugCaseUpdate,
) -> DebugCase:
    """실제 원인과 정답 정보를 기록한다."""

    values = update_data.model_dump(
        exclude_unset=True
    )

    for field_name, value in values.items():
        setattr(
            debug_case,
            field_name,
            value,
        )

    db.commit()
    db.refresh(debug_case)

    return debug_case


def delete_debug_case(
    db: Session,
    debug_case: DebugCase,
) -> None:
    """디버깅 사례를 삭제한다."""

    db.delete(debug_case)
    db.commit()