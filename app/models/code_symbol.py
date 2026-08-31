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


class CodeSymbol(Base):
    """AST에서 추출한 Java 코드 Symbol."""

    __tablename__ = "code_symbols"

    __table_args__ = (
        UniqueConstraint(
            "source_file_id",
            "symbol_type",
            "symbol_name",
            "start_line",
            name="uq_code_symbol_location",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_file_id: Mapped[int] = mapped_column(
        ForeignKey(
            "source_files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
    )

    package_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    class_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    symbol_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    symbol_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )