from pydantic import BaseModel, Field


class EmbeddingIndexRequest(BaseModel):
    """코드 조각 임베딩 요청."""

    force: bool = Field(
        default=False,
        description="기존 임베딩도 다시 생성할지 여부",
    )

    batch_size: int = Field(
        default=50,
        ge=1,
        le=100,
        description="한 번의 API 호출에 포함할 조각 수",
    )


class EmbeddingIndexResponse(BaseModel):
    """임베딩 처리 결과."""

    project_id: int
    total_chunks: int
    embedded_chunks: int
    skipped_chunks: int
    model: str


class CodeSearchRequest(BaseModel):
    """관련 코드 검색 요청."""

    query: str = Field(
        min_length=3,
        max_length=5000,
        examples=[
            "존재하지 않는 사용자 ID에서 NullPointerException이 발생합니다."
        ],
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
    )


class CodeSearchResult(BaseModel):
    """코드 검색 결과 한 건."""

    chunk_id: int
    source_file_id: int

    file_path: str

    start_line: int
    end_line: int

    content: str

    distance: float

    # 순수 embedding cosine similarity
    similarity: float

    # 하이브리드 검색 점수
    filename_score: float = 0.0
    keyword_score: float = 0.0

    hybrid_score: float | None = None


class CodeSearchResponse(BaseModel):
    """코드 검색 전체 응답."""

    project_id: int

    query: str

    retrieval_mode: str

    results: list[CodeSearchResult]