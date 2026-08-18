from pydantic import BaseModel, Field


class RetrievalEvaluationRequest(BaseModel):
    """검색 성능 평가 요청."""

    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="평가할 최대 DebugCase 수",
    )


class RetrievalMetrics(BaseModel):
    """Top-K 검색 정확도."""

    top_1_accuracy: float
    top_3_accuracy: float
    top_5_accuracy: float


class RetrievalCaseResult(BaseModel):
    """개별 디버깅 사례의 검색 결과."""

    debug_case_id: int

    expected_file: str

    vector_rank: int | None
    hybrid_rank: int | None


class RetrievalEvaluationResponse(BaseModel):
    """프로젝트 검색 평가 결과."""

    project_id: int

    ground_truth_cases: int
    evaluated_cases: int
    skipped_cases: int

    vector: RetrievalMetrics
    hybrid: RetrievalMetrics

    cases: list[RetrievalCaseResult]