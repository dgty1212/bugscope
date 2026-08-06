from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CodeChunk(Base):
    """검색과 임베딩에 사용할 소스코드 조각."""

    __tablename__ = "code_chunks"

    __table_args__ = (
        UniqueConstraint(
            "source_file_id",
            "chunk_index",
            name="uq_code_chunks_source_file_index",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_file_id: Mapped[int] = mapped_column(
        ForeignKey("source_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    language: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="java",
    )

    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    chunk_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="line_range",
    )

    symbol_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    start_line: Mapped[int] = mapped_column(
        nullable=False,
    )

    end_line: Mapped[int] = mapped_column(
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )