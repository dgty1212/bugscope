from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.models
from app.api.indexing import router as indexing_router
from app.api.projects import router as projects_router
from app.api.retrieval import router as retrieval_router
from app.api.source_file import router as source_file_router
from app.core.database import Base, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 아직 없는 DB 테이블을 생성한다."""

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="BugScope API",
    description="RAG 기반 소스코드 검색 및 오류 분석 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(projects_router)
app.include_router(source_file_router)
app.include_router(indexing_router)
app.include_router(retrieval_router)

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
def database_health_check(
    db: DbSession,
) -> dict[str, str | int]:
    try:
        result = db.execute(text("SELECT 1")).scalar_one()

        return {
            "status": "ok",
            "database": "connected",
            "result": result,
        }

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스에 연결할 수 없습니다.",
        ) from error