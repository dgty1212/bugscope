from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class DebugAnalysisRequest(BaseModel):
    """디버깅 분석 요청."""

    error_log: str = Field(
        min_length=1,
        max_length=20000,
    )

    situation: str | None = Field(
        default=None,
        max_length=5000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )
    
    retrieval_mode: Literal[
        "vector",
        "hybrid",
    ] = "hybrid"


class RetrievedChunk(BaseModel):
    chunk_id: int
    source_file_id: int

    file_path: str

    start_line: int
    end_line: int

    similarity: float

    filename_score: float = 0.0
    keyword_score: float = 0.0

    hybrid_score: float | None = None


class RootCause(BaseModel):
    """오류 원인 후보."""

    model_config = ConfigDict(extra="forbid")

    title: str

    file_path: str | None
    start_line: int | None
    end_line: int | None

    reason: str

    evidence_chunk_ids: list[int]

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class DebugAnalysisResult(BaseModel):
    """LLM이 반환하는 구조화된 분석 결과."""

    model_config = ConfigDict(extra="forbid")

    summary: str

    root_causes: list[RootCause]

    verification_steps: list[str]

    suggested_fixes: list[str]

    insufficient_context: bool

    additional_information_needed: list[str]


class DebugAnalysisResponse(BaseModel):
    """최종 API 응답."""
    
    debug_case_id: int
    
    project_id: int

    retrieval_query: str

    retrieved_chunks: list[RetrievedChunk]

    analysis: DebugAnalysisResult