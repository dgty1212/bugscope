from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CodeCall(Base):
    """Java method invocation 관계."""

    __tablename__ = "code_calls"

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

    caller_symbol_id: Mapped[int] = mapped_column(
        ForeignKey(
            "code_symbols.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    caller_class: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    caller_symbol: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    receiver: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    callee_class: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    callee_symbol: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    resolved_callee_symbol_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "code_symbols.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    line_number: Mapped[int] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )