from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 환경 설정."""

    database_url: str
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_analysis_model: str = "gpt-5.4-mini"
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """환경 설정 객체를 한 번만 생성해서 재사용한다."""
    return Settings()