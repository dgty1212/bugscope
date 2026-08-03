import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db


logger = logging.getLogger(__name__)

app = FastAPI(
    title="BugScope API",
    description="RAG 기반 소스코드 검색 및 오류 분석 API",
    version="0.1.0",
)


DbSession = Annotated[Session, Depends(get_db)]


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": "BugScope",
        "message": "API 서버가 정상적으로 실행 중입니다.",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def database_health_check(db: DbSession) -> dict[str, str | int]:
    """PostgreSQL 연결 상태를 확인한다."""

    try:
        result = db.execute(text("SELECT 1")).scalar_one()

        return {
            "status": "ok",
            "database": "connected",
            "result": result,
        }

    except SQLAlchemyError as exc:
        logger.exception("PostgreSQL 연결 확인 실패")
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스에 연결할 수 없습니다.",
        ) from exc