import hashlib
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.source_file import SourceFile


MAX_FILE_SIZE = 1024 * 1024  # 1MB
ALLOWED_EXTENSIONS = {".java"}


class SourceFileError(Exception):
    """소스 파일 처리 기본 예외."""


class UnsupportedSourceFileError(SourceFileError):
    """지원하지 않는 확장자."""


class EmptySourceFileError(SourceFileError):
    """빈 파일."""


class SourceFileTooLargeError(SourceFileError):
    """최대 크기를 초과한 파일."""


class SourceFileDecodeError(SourceFileError):
    """UTF-8로 읽을 수 없는 파일."""


class DuplicateSourceFileError(SourceFileError):
    """동일한 파일 경로나 내용이 이미 존재함."""


def create_source_file(
    db: Session,
    project_id: int,
    file_name: str,
    file_path: str,
    content_bytes: bytes,
) -> SourceFile:
    """업로드된 소스 파일을 검증하고 저장한다."""

    extension = Path(file_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedSourceFileError

    if not content_bytes:
        raise EmptySourceFileError

    if len(content_bytes) > MAX_FILE_SIZE:
        raise SourceFileTooLargeError

    try:
        # UTF-8 BOM이 포함된 파일도 처리한다.
        content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise SourceFileDecodeError from error

    if not content.strip():
        raise EmptySourceFileError

    normalized_path = file_path.strip().replace("\\", "/")

    if not normalized_path:
        normalized_path = file_name

    content_hash = hashlib.sha256(content_bytes).hexdigest()

    duplicate_statement = select(SourceFile).where(
        SourceFile.project_id == project_id,
        or_(
            SourceFile.file_path == normalized_path,
            SourceFile.content_hash == content_hash,
        ),
    )

    duplicate_file = db.scalar(duplicate_statement)

    if duplicate_file is not None:
        raise DuplicateSourceFileError

    source_file = SourceFile(
        project_id=project_id,
        file_name=file_name,
        file_path=normalized_path,
        language="java",
        content=content,
        content_hash=content_hash,
        file_size=len(content_bytes),
    )

    db.add(source_file)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise DuplicateSourceFileError from error

    db.refresh(source_file)

    return source_file


def get_source_files(
    db: Session,
    project_id: int,
) -> list[SourceFile]:
    """프로젝트에 등록된 소스 파일 목록을 조회한다."""

    statement = (
        select(SourceFile)
        .where(SourceFile.project_id == project_id)
        .order_by(SourceFile.id.desc())
    )

    return list(db.scalars(statement).all())


def get_source_file(
    db: Session,
    project_id: int,
    file_id: int,
) -> SourceFile | None:
    """특정 프로젝트의 소스 파일을 조회한다."""

    statement = select(SourceFile).where(
        SourceFile.id == file_id,
        SourceFile.project_id == project_id,
    )

    return db.scalar(statement)


def delete_source_file(
    db: Session,
    source_file: SourceFile,
) -> None:
    """소스 파일을 삭제한다."""

    db.delete(source_file)
    db.commit()