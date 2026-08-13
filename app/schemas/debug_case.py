from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DebugCaseUpdate(BaseModel):
    """분석 이후 사람이 입력하는 실제 결과."""

    actual_cause: str | None = Field(
        default=None,
        max_length=10000,
    )

    expected_file: str | None = Field(
        default=None,
        max_length=1000,
    )

    expected_symbol: str | None = Field(
        default=None,
        max_length=500,
    )

    resolved: bool | None = None

    user_score: float | None = Field(
        default=None,
        ge=0.0,
        le=5.0,
    )


class DebugCaseSummary(BaseModel):
    """디버깅 사례 목록."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int

    situation: str | None

    expected_file: str | None
    expected_symbol: str | None

    resolved: bool
    user_score: float | None

    created_at: datetime


class DebugCaseDetail(DebugCaseSummary):
    """디버깅 사례 상세."""

    error_log: str
    retrieval_query: str

    retrieved_chunks: list[dict[str, Any]]
    analysis_result: dict[str, Any]

    actual_cause: str | None

    updated_at: datetime