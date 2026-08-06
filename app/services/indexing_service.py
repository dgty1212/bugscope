from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunk
from app.models.source_file import SourceFile
from app.services.code_chunker import split_source_code


class NoSourceFilesError(Exception):
    """프로젝트에 등록된 소스 파일이 없을 때 발생."""


class ProjectIndexingError(Exception):
    """프로젝트 인덱싱에 실패했을 때 발생."""


@dataclass(frozen=True, slots=True)
class IndexingResult:
    """프로젝트 인덱싱 결과."""

    indexed_files: int
    created_chunks: int


def index_project(
    db: Session,
    project_id: int,
    max_lines: int = 100,
    overlap_lines: int = 20,
) -> IndexingResult:
    """프로젝트의 모든 소스 파일을 코드 조각으로 저장한다."""

    source_file_statement = (
        select(SourceFile)
        .where(SourceFile.project_id == project_id)
        .order_by(SourceFile.id)
    )

    source_files = list(
        db.scalars(source_file_statement).all()
    )

    if not source_files:
        raise NoSourceFilesError

    code_chunks: list[CodeChunk] = []

    for source_file in source_files:
        chunk_data_list = split_source_code(
            content=source_file.content,
            max_lines=max_lines,
            overlap_lines=overlap_lines,
        )

        for chunk_data in chunk_data_list:
            code_chunks.append(
                CodeChunk(
                    project_id=project_id,
                    source_file_id=source_file.id,
                    file_path=source_file.file_path,
                    language=source_file.language,
                    chunk_index=chunk_data.chunk_index,
                    chunk_type="line_range",
                    symbol_name=None,
                    start_line=chunk_data.start_line,
                    end_line=chunk_data.end_line,
                    content=chunk_data.content,
                    content_hash=chunk_data.content_hash,
                )
            )

    try:
        # 재인덱싱할 때 기존 코드 조각을 먼저 제거한다.
        db.execute(
            delete(CodeChunk).where(
                CodeChunk.project_id == project_id
            )
        )

        db.add_all(code_chunks)
        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        raise ProjectIndexingError from error

    return IndexingResult(
        indexed_files=len(source_files),
        created_chunks=len(code_chunks),
    )


def get_code_chunks(
    db: Session,
    project_id: int,
    offset: int = 0,
    limit: int = 100,
) -> list[CodeChunk]:
    """프로젝트에 저장된 코드 조각을 조회한다."""

    statement = (
        select(CodeChunk)
        .where(CodeChunk.project_id == project_id)
        .order_by(
            CodeChunk.source_file_id,
            CodeChunk.chunk_index,
        )
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def get_code_chunk(
    db: Session,
    project_id: int,
    chunk_id: int,
) -> CodeChunk | None:
    """특정 프로젝트의 코드 조각 하나를 조회한다."""

    statement = select(CodeChunk).where(
        CodeChunk.id == chunk_id,
        CodeChunk.project_id == project_id,
    )

    return db.scalar(statement)