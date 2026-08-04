from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceFileSummary(BaseModel):
    """소스 파일 목록과 업로드 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    file_name: str
    file_path: str
    language: str
    content_hash: str
    file_size: int
    created_at: datetime


class SourceFileDetail(SourceFileSummary):
    """소스 파일 상세 응답."""

    content: str