from openai import OpenAI, OpenAIError

from app.core.config import get_settings
from app.core.constants import EMBEDDING_DIMENSIONS


class EmbeddingGenerationError(Exception):
    """임베딩 생성 실패."""


settings = get_settings()

client = OpenAI(
    api_key=settings.openai_api_key,
)


def create_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """여러 문자열의 임베딩을 생성한다."""

    if not texts:
        return []

    if any(not text.strip() for text in texts):
        raise EmbeddingGenerationError(
            "빈 문자열은 임베딩할 수 없습니다."
        )

    try:
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
            encoding_format="float",
        )
    except OpenAIError as error:
        raise EmbeddingGenerationError(
            "OpenAI 임베딩 API 호출에 실패했습니다."
        ) from error

    ordered_data = sorted(
        response.data,
        key=lambda item: item.index,
    )

    embeddings = [
        item.embedding
        for item in ordered_data
    ]

    if len(embeddings) != len(texts):
        raise EmbeddingGenerationError(
            "요청한 문자열 수와 반환된 임베딩 수가 다릅니다."
        )

    for embedding in embeddings:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise EmbeddingGenerationError(
                f"임베딩 차원이 {EMBEDDING_DIMENSIONS}이 아닙니다."
            )

    return embeddings


def create_embedding(
    text: str,
) -> list[float]:
    """문자열 하나의 임베딩을 생성한다."""

    embeddings = create_embeddings([text])

    return embeddings[0]