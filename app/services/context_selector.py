from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.models.code_symbol import CodeSymbol
from app.services.retrieval_service import (
    SearchHit,
    search_code_chunks_hybrid,
)
from app.services.stack_trace_parser import parse_stack_trace
from app.services.symbol_index_service import (
    find_symbol_for_stack_frame,
    get_callees,
    get_callers,
)

ContextType = Literal[
    "trace",
    "callee",
    "caller",
    "semantic",
]

SourceType = Literal[
    "symbol",
    "chunk",
]


@dataclass(frozen=True, slots=True)
class SelectedContext:
    """LLM 분석에 전달할 코드 Context."""

    context_type: ContextType
    source_type: SourceType

    source_id: int

    file_path: str
    class_name: str | None
    symbol_name: str | None

    start_line: int
    end_line: int

    content: str

    score: float | None = None


def symbol_to_context(
    symbol: CodeSymbol,
    context_type: ContextType,
) -> SelectedContext:
    """CodeSymbol을 SelectedContext로 변환한다."""

    return SelectedContext(
        context_type=context_type,
        source_type="symbol",
        source_id=symbol.id,
        file_path=symbol.file_path,
        class_name=symbol.class_name,
        symbol_name=symbol.symbol_name,
        start_line=symbol.start_line,
        end_line=symbol.end_line,
        content=symbol.content,
    )


def search_hit_to_context(
    hit: SearchHit,
) -> SelectedContext:
    """검색 결과 CodeChunk를 SelectedContext로 변환한다."""

    chunk = hit.code_chunk

    score = (
        hit.hybrid_score
        if hit.hybrid_score is not None
        else hit.similarity
    )

    return SelectedContext(
        context_type="semantic",
        source_type="chunk",
        source_id=chunk.id,
        file_path=chunk.file_path,
        class_name=None,
        symbol_name=chunk.symbol_name,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        content=chunk.content,
        score=score,
    )


def search_hits_to_contexts(
    hits: list[SearchHit],
) -> list[SelectedContext]:
    """여러 검색 결과를 Context 목록으로 변환한다."""

    return [
        search_hit_to_context(hit)
        for hit in hits
    ]


def context_key(
    context: SelectedContext,
) -> tuple[str, int, int]:
    """Context 중복 제거에 사용할 키."""

    return (
        context.file_path,
        context.start_line,
        context.end_line,
    )


def append_context_if_unique(
    selected: list[SelectedContext],
    selected_keys: set[tuple[str, int, int]],
    context: SelectedContext,
) -> bool:
    """
    중복되지 않은 Context만 추가한다.

    추가되면 True,
    이미 존재하면 False를 반환한다.
    """

    key = context_key(context)

    if key in selected_keys:
        return False

    selected.append(context)
    selected_keys.add(key)

    return True


def select_debug_context(
    db: Session,
    project_id: int,
    error_log: str,
    retrieval_query: str,
    max_contexts: int = 8,
) -> list[SelectedContext]:
    """
    Stack Trace 구조 분석과 Hybrid Retrieval을 결합하여
    LLM에 전달할 Context를 선별한다.

    우선순위:
    1. TRACE
    2. CALLEE
    3. CALLER
    4. SEMANTIC
    """

    if max_contexts <= 0:
        return []

    parsed = parse_stack_trace(
        error_log,
    )

    selected: list[SelectedContext] = []

    selected_keys: set[
        tuple[str, int, int]
    ] = set()

    trace_symbols: list[CodeSymbol] = []

    # -------------------------------------------------
    # 1. TRACE
    # Stack Trace와 직접 일치하는 Symbol
    # -------------------------------------------------
    for frame in parsed.frames:
        symbol = find_symbol_for_stack_frame(
            db=db,
            project_id=project_id,
            frame=frame,
        )

        if symbol is None:
            continue

        # 동일 Symbol이 여러 stack frame에서
        # 중복되는 경우 방지
        if all(
            existing.id != symbol.id
            for existing in trace_symbols
        ):
            trace_symbols.append(symbol)

        context = symbol_to_context(
            symbol=symbol,
            context_type="trace",
        )

        append_context_if_unique(
            selected=selected,
            selected_keys=selected_keys,
            context=context,
        )

        if len(selected) >= max_contexts:
            return selected

    # -------------------------------------------------
    # 2. CALLEE
    # Trace 함수가 직접 호출하는 함수
    # -------------------------------------------------
    for symbol in trace_symbols:
        callees = get_callees(
            db=db,
            symbol_id=symbol.id,
        )

        for callee in callees:
            context = symbol_to_context(
                symbol=callee,
                context_type="callee",
            )

            append_context_if_unique(
                selected=selected,
                selected_keys=selected_keys,
                context=context,
            )

            if len(selected) >= max_contexts:
                return selected

    # -------------------------------------------------
    # 3. CALLER
    # Trace 함수를 호출하는 함수
    # -------------------------------------------------
    for symbol in trace_symbols:
        callers = get_callers(
            db=db,
            symbol_id=symbol.id,
        )

        for caller in callers:
            context = symbol_to_context(
                symbol=caller,
                context_type="caller",
            )

            append_context_if_unique(
                selected=selected,
                selected_keys=selected_keys,
                context=context,
            )

            if len(selected) >= max_contexts:
                return selected

    # -------------------------------------------------
    # 4. SEMANTIC
    # 남은 Context를 Hybrid Retrieval로 보완
    # -------------------------------------------------
    remaining_contexts = (
        max_contexts - len(selected)
    )

    if remaining_contexts <= 0:
        return selected

    # 중복 후보가 있을 수 있으므로
    # 필요한 수보다 넉넉하게 검색한다.
    candidate_k = max(
        remaining_contexts * 3,
        max_contexts,
    )

    hybrid_hits = search_code_chunks_hybrid(
        db=db,
        project_id=project_id,
        query=retrieval_query,
        top_k=candidate_k,
    )

    for hit in hybrid_hits:
        context = search_hit_to_context(
            hit
        )

        append_context_if_unique(
            selected=selected,
            selected_keys=selected_keys,
            context=context,
        )

        if len(selected) >= max_contexts:
            break

    return selected