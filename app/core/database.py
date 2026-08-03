from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# 애플리케이션 전체에서 하나의 Engine을 재사용한다.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# 요청마다 DB 세션을 생성하기 위한 팩토리다.
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """향후 SQLAlchemy 모델이 상속받을 기본 클래스."""



def get_db() -> Generator[Session, None, None]:
    """FastAPI 요청마다 DB 세션을 제공하고 요청 종료 후 닫는다."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()