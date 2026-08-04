from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.source_file import SourceFileDetail, SourceFileSummary
from app.services import project_service, source_file_service
from app.services.source_file_service import (
    DuplicateSourceFileError,
    EmptySourceFileError,
    SourceFileDecodeError,
    SourceFileTooLargeError,
    UnsupportedSourceFileError,
)


router = APIRouter(
    prefix="/projects/{project_id}/files",
    tags=["source-files"],
)

DbSession = Annotated[Session, Depends(get_db)]


def validate_project_exists(
    db: Session,
    project_id: int,
) -> None:
    """프로젝트 존재 여부를 확인한다."""

    project = project_service.get_project(
        db=db,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )


@router.post(
    "",
    response_model=SourceFileSummary,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source_file(
    project_id: int,
    db: DbSession,
    file: Annotated[
        UploadFile,
        File(description="업로드할 Java 소스 파일"),
    ],
    file_path: Annotated[
        str | None,
        Form(description="프로젝트 내부 파일 경로"),
    ] = None,
) -> SourceFileSummary:
    """프로젝트에 Java 소스 파일을 업로드한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일 이름이 없습니다.",
        )

    # 최대 크기보다 한 바이트 더 읽어서 초과 여부를 검사한다.
    content_bytes = await file.read(
        source_file_service.MAX_FILE_SIZE + 1
    )

    stored_path = file_path or file.filename

    try:
        return source_file_service.create_source_file(
            db=db,
            project_id=project_id,
            file_name=file.filename,
            file_path=stored_path,
            content_bytes=content_bytes,
        )

    except UnsupportedSourceFileError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=".java 파일만 업로드할 수 있습니다.",
        ) from error

    except EmptySourceFileError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="빈 소스 파일은 업로드할 수 없습니다.",
        ) from error

    except SourceFileTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="파일 크기는 1MB를 초과할 수 없습니다.",
        ) from error

    except SourceFileDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="소스 파일을 UTF-8 형식으로 읽을 수 없습니다.",
        ) from error

    except DuplicateSourceFileError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="동일한 경로나 내용을 가진 파일이 이미 존재합니다.",
        ) from error

    finally:
        await file.close()


@router.get(
    "",
    response_model=list[SourceFileSummary],
)
def get_source_files(
    project_id: int,
    db: DbSession,
) -> list[SourceFileSummary]:
    """프로젝트의 소스 파일 목록을 조회한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    return source_file_service.get_source_files(
        db=db,
        project_id=project_id,
    )


@router.get(
    "/{file_id}",
    response_model=SourceFileDetail,
)
def get_source_file(
    project_id: int,
    file_id: int,
    db: DbSession,
) -> SourceFileDetail:
    """소스 파일 내용까지 상세 조회한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    source_file = source_file_service.get_source_file(
        db=db,
        project_id=project_id,
        file_id=file_id,
    )

    if source_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소스 파일을 찾을 수 없습니다.",
        )

    return source_file


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_source_file(
    project_id: int,
    file_id: int,
    db: DbSession,
) -> Response:
    """프로젝트의 소스 파일을 삭제한다."""

    validate_project_exists(
        db=db,
        project_id=project_id,
    )

    source_file = source_file_service.get_source_file(
        db=db,
        project_id=project_id,
        file_id=file_id,
    )

    if source_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소스 파일을 찾을 수 없습니다.",
        )

    source_file_service.delete_source_file(
        db=db,
        source_file=source_file,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)