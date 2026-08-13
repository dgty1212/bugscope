from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DebugCase(Base):
    """BugScope가 분석한 디버깅 사례."""

    __tablename__ = "debug_cases"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    error_log: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    situation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    retrieval_query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    retrieved_chunks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )

    analysis_result: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # 사람이 나중에 입력하는 실제 정답
    actual_cause: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    expected_file: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    expected_symbol: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    user_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )