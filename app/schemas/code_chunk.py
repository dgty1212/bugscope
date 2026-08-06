from datetime import datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class ProjectIndexRequest(BaseModel):
    """프로젝트 코드 인덱싱 요청."""

    max_lines: int = Field(
        default=100,
        ge=10,
        le=500,
        description="한 코드 조각에 들어갈 최대 줄 수",
    )

    overlap_lines: int = Field(
        default=20,
        ge=0,
        le=200,
        description="이전 조각과 중복할 줄 수",
    )

    @model_validator(mode="after")
    def validate_chunk_options(self) -> Self:
        if self.overlap_lines >= self.max_lines:
            raise ValueError(
                "overlap_lines는 max_lines보다 작아야 합니다."
            )

        return self


class ProjectIndexResponse(BaseModel):
    """프로젝트 인덱싱 결과."""

    project_id: int
    indexed_files: int
    created_chunks: int
    max_lines: int
    overlap_lines: int


class CodeChunkResponse(BaseModel):
    """코드 조각 조회 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    source_file_id: int

    file_path: str
    language: str

    chunk_index: int
    chunk_type: str
    symbol_name: str | None

    start_line: int
    end_line: int

    content: str
    content_hash: str
    created_at: datetime