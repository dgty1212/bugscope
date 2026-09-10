from pydantic import BaseModel, Field

class StructuralUsageMetricsResponse(BaseModel):
    total_cases: int

    trace_cases: int
    caller_cases: int
    callee_cases: int
    semantic_only_cases: int

    trace_rate: float
    caller_rate: float
    callee_rate: float
    semantic_only_rate: float
    
class RetrievalModeMetricsResponse(BaseModel):
    evaluated_cases: int
    symbol_cases: int

    file_top1: float
    file_top3: float
    file_top5: float
    file_mrr: float

    symbol_top1: float | None
    symbol_top3: float | None
    symbol_top5: float | None
    symbol_mrr: float | None

    average_context_count: float    
    
class ComparativeCaseEvaluationResponse(
    BaseModel
):
    debug_case_id: int

    expected_file: str
    expected_symbol: str | None

    vector_file_rank: int | None
    hybrid_file_rank: int | None
    structural_file_rank: int | None

    vector_symbol_rank: int | None
    hybrid_symbol_rank: int | None
    structural_symbol_rank: int | None
    
    structural_context_types: list[str]
    structural_context_details: list[str]
    
class ComparativeRetrievalEvaluationResponse(BaseModel):
    project_id: int
    evaluated_cases: int

    vector: RetrievalModeMetricsResponse
    hybrid: RetrievalModeMetricsResponse
    structural: RetrievalModeMetricsResponse
    
    cases: list[
        ComparativeCaseEvaluationResponse
    ]
    
    structural_usage: StructuralUsageMetricsResponse    


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
    
