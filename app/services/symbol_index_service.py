from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.code_call import CodeCall
from app.models.code_symbol import CodeSymbol
from app.models.source_file import SourceFile
from app.schemas.stack_trace import StackFrame
from app.services.java_ast_parser import (
    extract_java_method_calls,
    extract_java_symbols,
)


@dataclass(frozen=True, slots=True)
class SymbolIndexResult:
    indexed_files: int
    created_symbols: int
    created_calls: int


def index_project_symbols(
    db: Session,
    project_id: int,
) -> SymbolIndexResult:
    print("[STRUCTURE] 1. source files 조회 시작", flush=True)

    statement = (
        select(SourceFile)
        .where(
            SourceFile.project_id == project_id
        )
        .order_by(SourceFile.id)
    )

    source_files = list(
        db.scalars(statement).all()
    )

    print(
        f"[STRUCTURE] 2. source files 조회 완료: "
        f"{len(source_files)}개",
        flush=True,
    )

    print("[STRUCTURE] 3. 기존 CodeCall 삭제", flush=True)

    db.execute(
        delete(CodeCall).where(
            CodeCall.project_id == project_id
        )
    )

    print("[STRUCTURE] 4. 기존 CodeSymbol 삭제", flush=True)

    db.execute(
        delete(CodeSymbol).where(
            CodeSymbol.project_id == project_id
        )
    )

    db.flush()

    print("[STRUCTURE] 5. 기존 데이터 삭제 완료", flush=True)

    created_symbols: list[CodeSymbol] = []
    java_files: list[SourceFile] = []

    print("[STRUCTURE] 6. AST Symbol 생성 시작", flush=True)

    for source_file in source_files:
        if source_file.language != "java":
            continue

        print(
            f"[STRUCTURE] AST: {source_file.file_path}",
            flush=True,
        )

        java_files.append(source_file)

        parsed_symbols = extract_java_symbols(
            source_file.content
        )

        print(
            f"[STRUCTURE]   symbols={len(parsed_symbols)}",
            flush=True,
        )

        for symbol in parsed_symbols:
            model = CodeSymbol(
                project_id=project_id,
                source_file_id=source_file.id,
                file_path=source_file.file_path,
                package_name=symbol.package_name,
                class_name=symbol.class_name,
                symbol_name=symbol.symbol_name,
                symbol_type=symbol.symbol_type,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                content=symbol.content,
            )

            db.add(model)
            created_symbols.append(model)

    print(
        f"[STRUCTURE] 7. Symbol 생성 완료: "
        f"{len(created_symbols)}개",
        flush=True,
    )

    print("[STRUCTURE] 8. Symbol flush 시작", flush=True)

    db.flush()

    print("[STRUCTURE] 9. Symbol flush 완료", flush=True)

    created_calls: list[CodeCall] = []

    print("[STRUCTURE] 10. Call Graph 생성 시작", flush=True)

    for source_file in java_files:
        print(
            f"[STRUCTURE] CALLS: {source_file.file_path}",
            flush=True,
        )

        file_symbols = [
            symbol
            for symbol in created_symbols
            if symbol.source_file_id == source_file.id
        ]

        method_calls = extract_java_method_calls(
            source_file.content
        )

        print(
            f"[STRUCTURE]   calls={len(method_calls)}",
            flush=True,
        )

        for call in method_calls:
            caller = find_caller_symbol(
                file_symbols,
                class_name=call.caller_class,
                method_name=call.caller_method,
                line_number=call.line_number,
            )

            if caller is None:
                continue

            callee = resolve_callee_symbol(
                created_symbols,
                callee_name=call.callee_name,
                callee_class=call.inferred_callee_class,
            )

            model = CodeCall(
                project_id=project_id,
                source_file_id=source_file.id,
                caller_symbol_id=caller.id,
                caller_class=call.caller_class,
                caller_symbol=call.caller_method,
                receiver=call.receiver,
                callee_class=call.inferred_callee_class,
                callee_symbol=call.callee_name,
                resolved_callee_symbol_id=(
                    callee.id
                    if callee is not None
                    else None
                ),
                line_number=call.line_number,
            )

            db.add(model)
            created_calls.append(model)

    print(
        f"[STRUCTURE] 11. Call 생성 완료: "
        f"{len(created_calls)}개",
        flush=True,
    )

    print("[STRUCTURE] 12. commit 시작", flush=True)

    db.commit()

    print("[STRUCTURE] 13. commit 완료", flush=True)

    return SymbolIndexResult(
        indexed_files=len(java_files),
        created_symbols=len(created_symbols),
        created_calls=len(created_calls),
    )
    
    
def get_callees(
    db: Session,
    symbol_id: int,
) -> list[CodeSymbol]:
    statement = (
        select(CodeCall)
        .where(
            CodeCall.caller_symbol_id
            == symbol_id,
            CodeCall.resolved_callee_symbol_id
            .is_not(None),
        )
        .order_by(CodeCall.line_number)
    )

    calls = list(
        db.scalars(statement).all()
    )

    results: list[CodeSymbol] = []

    for call in calls:
        if (
            call.resolved_callee_symbol_id
            is None
        ):
            continue

        symbol = db.get(
            CodeSymbol,
            call.resolved_callee_symbol_id,
        )

        if symbol is not None:
            results.append(symbol)

    return results

def get_callers(
    db: Session,
    symbol_id: int,
) -> list[CodeSymbol]:
    statement = (
        select(CodeCall)
        .where(
            CodeCall.resolved_callee_symbol_id
            == symbol_id
        )
    )

    calls = list(
        db.scalars(statement).all()
    )

    results: list[CodeSymbol] = []

    for call in calls:
        symbol = db.get(
            CodeSymbol,
            call.caller_symbol_id,
        )

        if symbol is not None:
            results.append(symbol)

    return results

def find_symbol_for_stack_frame(
    db: Session,
    project_id: int,
    frame: StackFrame,
) -> CodeSymbol | None:
    """StackFrame에 가장 잘 대응하는 CodeSymbol을 찾는다."""

    statement = select(CodeSymbol).where(
        CodeSymbol.project_id == project_id,
        CodeSymbol.symbol_type.in_(
            ("method", "constructor"),
        ),
        CodeSymbol.symbol_name == frame.method_name,
    )    
    
    candidates = list(
        db.scalars(statement).all()
    )

    if not candidates:
        return None

    # 1. 파일명 일치
    if frame.package_name is not None:
        package_matches = [
            symbol
            for symbol in candidates
            if (
                symbol.package_name is not None
                and symbol.package_name
                == frame.package_name
            )
        ]

        if package_matches:
            candidates = package_matches


    if frame.file_name is not None:
        normalized_file_name = (
            frame.file_name
            .replace("\\", "/")
            .lower()
        )

        file_matches = [
            symbol
            for symbol in candidates
            if (
                symbol.file_path
                .replace("\\", "/")
                .lower()
                .endswith(
                    "/" + normalized_file_name
                )
            )
        ]

        if file_matches:
            candidates = file_matches


    class_name = frame.class_name.split("$", 1)[0]

    class_matches = [
        symbol
        for symbol in candidates
        if symbol.class_name == class_name
    ]

    if class_matches:
        candidates = class_matches


    if frame.line_number is not None:
        line_matches = [
            symbol
            for symbol in candidates
            if (
                symbol.start_line
                <= frame.line_number
                <= symbol.end_line
            )
        ]

        if line_matches:
            return line_matches[0]

    # 2. 클래스명 일치
    class_name = frame.class_name.split("$", 1)[0]

    class_matches = [
        symbol
        for symbol in candidates
        if (
            symbol.class_name is not None
            and symbol.class_name == class_name
        )
    ]

    if class_matches:
        candidates = class_matches

    # 3. stack trace line이 symbol 범위에 들어가는지 확인
    if frame.line_number is not None:
        line_matches = [
            symbol
            for symbol in candidates
            if (
                symbol.start_line
                <= frame.line_number
                <= symbol.end_line
            )
        ]

        if line_matches:
            return line_matches[0]

    return candidates[0]

def find_caller_symbol(
    symbols: list[CodeSymbol],
    *,
    class_name: str | None,
    method_name: str,
    line_number: int,
) -> CodeSymbol | None:
    candidates = [
        symbol
        for symbol in symbols
        if (
            symbol.symbol_type
            in {"method", "constructor"}
            and symbol.symbol_name
            == method_name
        )
    ]

    if class_name is not None:
        class_matches = [
            symbol
            for symbol in candidates
            if symbol.class_name
            == class_name
        ]

        if class_matches:
            candidates = class_matches

    line_matches = [
        symbol
        for symbol in candidates
        if (
            symbol.start_line
            <= line_number
            <= symbol.end_line
        )
    ]

    if line_matches:
        return line_matches[0]

    if candidates:
        return candidates[0]

    return None

def resolve_callee_symbol(
    symbols: list[CodeSymbol],
    *,
    callee_name: str,
    callee_class: str | None,
) -> CodeSymbol | None:
    candidates = [
        symbol
        for symbol in symbols
        if (
            symbol.symbol_type
            in {"method", "constructor"}
            and symbol.symbol_name
            == callee_name
        )
    ]

    if not candidates:
        return None

    if callee_class is not None:
        class_matches = [
            symbol
            for symbol in candidates
            if symbol.class_name
            == callee_class
        ]

        if len(class_matches) == 1:
            return class_matches[0]

        if class_matches:
            candidates = class_matches

    # 프로젝트 전체에서 이름이 유일한 경우에만 추론
    if len(candidates) == 1:
        return candidates[0]

    return None