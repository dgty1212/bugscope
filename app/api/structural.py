from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.stack_trace import StackTraceAnalyzeRequest
from app.services.stack_trace_parser import parse_stack_trace
from app.services.symbol_index_service import (
    find_symbol_for_stack_frame,
    get_callees,
    get_callers,
    index_project_symbols,
)

router = APIRouter(
    prefix="/projects/{project_id}/structure",
    tags=["structure"],
)

DbSession = Annotated[
    Session,
    Depends(get_db),
]


@router.post("/index")
def index_structure(
    project_id: int,
    db: DbSession,
) -> dict[str, int]:
    result = index_project_symbols(
        db=db,
        project_id=project_id,
    )

    return {
        "indexed_files": result.indexed_files,
        "created_symbols": result.created_symbols,
        "created_calls": result.created_calls,
    }


@router.post("/trace")
def trace_stack(
    project_id: int,
    request: StackTraceAnalyzeRequest,
    db: DbSession,
) -> dict:
    parsed = parse_stack_trace(
        request.error_log,
    )

    results = []

    for frame in parsed.frames:
        # Stack Trace의 frame과 정확히 대응하는 코드 Symbol 탐색
        symbol = find_symbol_for_stack_frame(
            db=db,
            project_id=project_id,
            frame=frame,
        )

        # Symbol을 찾으면 Caller / Callee 조회
        if symbol is not None:
            callers = get_callers(
                db=db,
                symbol_id=symbol.id,
            )

            callees = get_callees(
                db=db,
                symbol_id=symbol.id,
            )
        else:
            callers = []
            callees = []

        # CodeSymbol 객체를 JSON 반환용 dict로 변환
        caller_data = [
            {
                "id": caller.id,
                "file_path": caller.file_path,
                "class_name": caller.class_name,
                "symbol_name": caller.symbol_name,
                "symbol_type": caller.symbol_type,
                "start_line": caller.start_line,
                "end_line": caller.end_line,
            }
            for caller in callers
        ]

        callee_data = [
            {
                "id": callee.id,
                "file_path": callee.file_path,
                "class_name": callee.class_name,
                "symbol_name": callee.symbol_name,
                "symbol_type": callee.symbol_type,
                "start_line": callee.start_line,
                "end_line": callee.end_line,
            }
            for callee in callees
        ]

        results.append(
            {
                "frame": frame.model_dump(),
                "matched_symbol": (
                    {
                        "id": symbol.id,
                        "file_path": symbol.file_path,
                        "class_name": symbol.class_name,
                        "symbol_name": symbol.symbol_name,
                        "symbol_type": symbol.symbol_type,
                        "start_line": symbol.start_line,
                        "end_line": symbol.end_line,
                    }
                    if symbol is not None
                    else None
                ),
                "callers": caller_data,
                "callees": callee_data,
            }
        )

    return {
        "exception_type": parsed.exception_type,
        "message": parsed.message,
        "matches": results,
    }