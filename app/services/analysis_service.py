from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.schemas.analysis import DebugAnalysisResult
from app.services import llm_service, retrieval_service
from app.services.context_selector import (
    SelectedContext,
    search_hits_to_contexts,
    select_debug_context,
)


@dataclass(frozen=True, slots=True)
class DebugAnalysisPipelineResult:
    """RAG 디버깅 파이프라인 실행 결과."""

    retrieval_query: str
    contexts: list[SelectedContext]
    analysis: DebugAnalysisResult


def build_retrieval_query(
    error_log: str,
    situation: str | None,
) -> str:
    """검색에 사용할 질의를 생성한다."""

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


def retrieve_analysis_contexts(
    db: Session,
    project_id: int,
    error_log: str,
    retrieval_query: str,
    retrieval_mode: str,
    top_k: int,
) -> list[SelectedContext]:
    """
    retrieval_mode에 따라 LLM 분석에 사용할
    Context를 가져온다.
    """

    if retrieval_mode == "vector":
        hits = retrieval_service.search_code_chunks(
            db=db,
            project_id=project_id,
            query=retrieval_query,
            top_k=top_k,
        )

        return search_hits_to_contexts(
            hits
        )

    if retrieval_mode == "hybrid":
        hits = (
            retrieval_service
            .search_code_chunks_hybrid(
                db=db,
                project_id=project_id,
                query=retrieval_query,
                top_k=top_k,
            )
        )

        return search_hits_to_contexts(
            hits
        )

    if retrieval_mode == "structural":
        return select_debug_context(
            db=db,
            project_id=project_id,
            error_log=error_log,
            retrieval_query=retrieval_query,
            max_contexts=top_k,
        )

    raise ValueError(
        f"지원하지 않는 retrieval_mode입니다: "
        f"{retrieval_mode}"
    )


def build_llm_prompt(
    error_log: str,
    situation: str | None,
    contexts: list[SelectedContext],
) -> str:
    """선별된 Context를 LLM 입력 Prompt로 변환한다."""

    context_sections: list[str] = []

    for context_id, context in enumerate(
        contexts,
        start=1,
    ):
        score_text = (
            f"{context.score:.4f}"
            if context.score is not None
            else "N/A"
        )

        context_sections.append(
            "\n".join(
                [
                    f"[CONTEXT {context_id}]",
                    (
                        f"role: "
                        f"{context.context_type.upper()}"
                    ),
                    (
                        f"source_type: "
                        f"{context.source_type}"
                    ),
                    (
                        f"source_id: "
                        f"{context.source_id}"
                    ),
                    (
                        f"file: "
                        f"{context.file_path}"
                    ),
                    (
                        f"class: "
                        f"{context.class_name or 'N/A'}"
                    ),
                    (
                        f"symbol: "
                        f"{context.symbol_name or 'N/A'}"
                    ),
                    (
                        f"lines: "
                        f"{context.start_line}-"
                        f"{context.end_line}"
                    ),
                    f"score: {score_text}",
                    "",
                    context.content,
                ]
            )
        )

    context_text = "\n\n".join(
        context_sections
    )

    return f"""
[ERROR LOG]
{error_log}

[SITUATION]
{situation or "제공되지 않음"}

[SELECTED CONTEXT]

{context_text}

[INSTRUCTION]

오류의 실제 원인을 분석하세요.

각 원인을 제시할 때 반드시 위의
[CONTEXT N] 중 근거로 사용한 번호를
evidence_context_ids에 기록하세요.

Stack Trace에 직접 대응하는 TRACE Context를
가장 신뢰도가 높은 근거로 취급하세요.

CALLEE Context는 잘못된 값이나 상태가
어디에서 생성되었는지 확인할 때 사용하세요.

CALLER Context는 오류가 어떤 실행 흐름에서
발생했는지 확인할 때 사용하세요.

SEMANTIC Context는 구조 분석에서 부족한
정보를 보완하는 근거로 사용하세요.

제공된 Context에 존재하지 않는
파일, 클래스, 메서드, 변수, 라인을
추측해서 만들어내지 마세요.
""".strip()


def analyze_debug_case(
    db: Session,
    project_id: int,
    error_log: str,
    situation: str | None,
    top_k: int,
    retrieval_mode: str = "structural",
) -> DebugAnalysisPipelineResult:
    """검색과 LLM 분석을 연결한 RAG 파이프라인."""

    retrieval_query = build_retrieval_query(
        error_log=error_log,
        situation=situation,
    )

    contexts = retrieve_analysis_contexts(
        db=db,
        project_id=project_id,
        error_log=error_log,
        retrieval_query=retrieval_query,
        retrieval_mode=retrieval_mode,
        top_k=top_k,
    )

    llm_prompt = build_llm_prompt(
        error_log=error_log,
        situation=situation,
        contexts=contexts,
    )

    analysis = llm_service.analyze_debug_context(
        user_prompt=llm_prompt,
    )

    return DebugAnalysisPipelineResult(
        retrieval_query=retrieval_query,
        contexts=contexts,
        analysis=analysis,
    )
    
from app.schemas.analysis import AnalysisContext


def build_analysis_contexts(
    contexts: list[SelectedContext],
) -> list[AnalysisContext]:
    return [
        AnalysisContext(
            context_id=context_id,
            context_type=context.context_type,
            source_type=context.source_type,
            source_id=context.source_id,
            file_path=context.file_path,
            class_name=context.class_name,
            symbol_name=context.symbol_name,
            start_line=context.start_line,
            end_line=context.end_line,
            score=context.score,
        )
        for context_id, context in enumerate(
            contexts,
            start=1,
        )
    ]