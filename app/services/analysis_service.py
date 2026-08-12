from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.schemas.analysis import DebugAnalysisResult
from app.services import llm_service, retrieval_service
from app.services.retrieval_service import SearchHit


@dataclass(frozen=True, slots=True)
class DebugAnalysisPipelineResult:
    """RAG 디버깅 파이프라인 실행 결과."""

    retrieval_query: str
    search_hits: list[SearchHit]
    analysis: DebugAnalysisResult


def build_retrieval_query(
    error_log: str,
    situation: str | None,
) -> str:
    """벡터 검색에 사용할 질의를 생성한다."""

    parts: list[str] = []

    if situation:
        parts.append(
            f"상황:\n{situation.strip()}"
        )

    # 검색용 임베딩 입력은 지나치게 길 필요가 없으므로
    # 오류 로그의 주요 앞부분만 사용한다.
    trimmed_error_log = error_log.strip()[:6000]

    parts.append(
        f"오류 로그:\n{trimmed_error_log}"
    )

    return "\n\n".join(parts)


def build_llm_prompt(
    error_log: str,
    situation: str | None,
    search_hits: list[SearchHit],
) -> str:
    """검색 결과와 로그를 LLM 입력 문맥으로 변환한다."""

    context_parts: list[str] = []

    for rank, hit in enumerate(
        search_hits,
        start=1,
    ):
        chunk = hit.code_chunk

        context_parts.append(
            "\n".join(
                [
                    f"<code_chunk rank=\"{rank}\">",
                    f"Chunk ID: {chunk.id}",
                    f"File: {chunk.file_path}",
                    (
                        "Lines: "
                        f"{chunk.start_line}-"
                        f"{chunk.end_line}"
                    ),
                    (
                        "Similarity: "
                        f"{hit.similarity:.4f}"
                    ),
                    "Code:",
                    "```java",
                    chunk.content,
                    "```",
                    "</code_chunk>",
                ]
            )
        )

    situation_text = (
        situation.strip()
        if situation
        else "추가 상황 설명 없음"
    )

    retrieved_context = "\n\n".join(
        context_parts
    )

    return f"""
<debug_case>

<error_log>
{error_log}
</error_log>

<situation>
{situation_text}
</situation>

<retrieved_source_code>
{retrieved_context}
</retrieved_source_code>

</debug_case>

위 오류 로그와 검색된 소스코드만을 근거로
오류의 가능한 원인을 분석하세요.

검색된 코드만으로 충분하지 않다면
그 사실을 명확하게 표시하세요.
""".strip()


def analyze_debug_case(
    db: Session,
    project_id: int,
    error_log: str,
    situation: str | None,
    top_k: int,
) -> DebugAnalysisPipelineResult:
    """검색과 LLM 분석을 연결한 RAG 파이프라인."""

    retrieval_query = build_retrieval_query(
        error_log=error_log,
        situation=situation,
    )

    search_hits = (
        retrieval_service.search_code_chunks(
            db=db,
            project_id=project_id,
            query=retrieval_query,
            top_k=top_k,
        )
    )

    llm_prompt = build_llm_prompt(
        error_log=error_log,
        situation=situation,
        search_hits=search_hits,
    )

    analysis = llm_service.analyze_debug_context(
        user_prompt=llm_prompt,
    )

    return DebugAnalysisPipelineResult(
        retrieval_query=retrieval_query,
        search_hits=search_hits,
        analysis=analysis,
    )