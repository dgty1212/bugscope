from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """프로젝트 생성 요청."""

    name: str = Field(
        min_length=1,
        max_length=100,
        examples=["sample-spring-project"],
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
        examples=["Spring Boot 오류 분석용 프로젝트"],
    )

    language: str = Field(
        default="java",
        min_length=1,
        max_length=30,
        examples=["java"],
    )


class ProjectUpdate(BaseModel):
    """프로젝트 수정 요청."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
    )

    language: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )


class ProjectResponse(BaseModel):
    """프로젝트 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    language: str
    created_at: datetime
    updated_at: datetime