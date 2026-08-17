from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.code_chunk import CodeChunk
from app.services.embedding_service import (
    EmbeddingGenerationError,
    create_embedding,
    create_embeddings,
)
from app.services.hybrid_retrieval import (
    calculate_hybrid_score,
    calculate_lexical_scores,
    extract_query_signals,
)

settings = get_settings()


class NoCodeChunksError(Exception):
    """인덱싱된 코드 조각이 없음."""


class NoEmbeddedChunksError(Exception):
    """임베딩이 생성된 코드 조각이 없음."""


class ProjectEmbeddingError(Exception):
    """프로젝트 임베딩 저장 실패."""


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    total_chunks: int
    embedded_chunks: int
    skipped_chunks: int


@dataclass(frozen=True, slots=True)
class SearchHit:
    code_chunk: CodeChunk

    distance: float
    similarity: float

    filename_score: float = 0.0
    keyword_score: float = 0.0

    hybrid_score: float | None = None


def build_embedding_text(
    code_chunk: CodeChunk,
) -> str:
    """코드 조각과 메타데이터를 임베딩용 문자열로 만든다."""

    return (
        f"File: {code_chunk.file_path}\n"
        f"Language: {code_chunk.language}\n"
        f"Lines: {code_chunk.start_line}-{code_chunk.end_line}\n"
        "Code:\n"
        f"{code_chunk.content}"
    )


def embed_project_chunks(
    db: Session,
    project_id: int,
    force: bool = False,
    batch_size: int = 50,
) -> EmbeddingResult:
    """프로젝트의 코드 조각에 임베딩을 생성한다."""

    all_chunks_statement = (
        select(CodeChunk)
        .where(CodeChunk.project_id == project_id)
        .order_by(CodeChunk.id)
    )

    all_chunks = list(
        db.scalars(all_chunks_statement).all()
    )

    if not all_chunks:
        raise NoCodeChunksError

    if force:
        target_chunks = all_chunks
    else:
        target_chunks = [
            chunk
            for chunk in all_chunks
            if chunk.embedding is None
        ]

    if not target_chunks:
        return EmbeddingResult(
            total_chunks=len(all_chunks),
            embedded_chunks=0,
            skipped_chunks=len(all_chunks),
        )

    processed_chunks = 0

    try:
        for start in range(0, len(target_chunks), batch_size):
            batch = target_chunks[start : start + batch_size]

            texts = [
                build_embedding_text(chunk)
                for chunk in batch
            ]

            embeddings = create_embeddings(texts)

            for chunk, embedding in zip(
                batch,
                embeddings,
                strict=True,
            ):
                chunk.embedding = embedding
                chunk.embedding_model = (
                    settings.openai_embedding_model
                )
                chunk.embedded_at = datetime.now(UTC)

                processed_chunks += 1

        db.commit()

    except (
        SQLAlchemyError,
        EmbeddingGenerationError,
    ) as error:
        db.rollback()
        raise ProjectEmbeddingError from error

    return EmbeddingResult(
        total_chunks=len(all_chunks),
        embedded_chunks=processed_chunks,
        skipped_chunks=len(all_chunks) - processed_chunks,
    )


def search_code_chunks(
    db: Session,
    project_id: int,
    query: str,
    top_k: int = 5,
) -> list[SearchHit]:
    """자연어 질의와 유사한 코드 조각을 검색한다."""

    embedded_chunk_exists = db.scalar(
        select(CodeChunk.id)
        .where(
            CodeChunk.project_id == project_id,
            CodeChunk.embedding.is_not(None),
        )
        .limit(1)
    )

    if embedded_chunk_exists is None:
        raise NoEmbeddedChunksError

    query_embedding = create_embedding(query)

    distance_expression = (
        CodeChunk.embedding
        .cosine_distance(query_embedding)
        .label("distance")
    )

    statement = (
        select(
            CodeChunk,
            distance_expression,
        )
        .where(
            CodeChunk.project_id == project_id,
            CodeChunk.embedding.is_not(None),
        )
        .order_by(distance_expression)
        .limit(top_k)
    )

    rows = db.execute(statement).all()

    results: list[SearchHit] = []

    for code_chunk, distance in rows:
        numeric_distance = float(distance)
        similarity = 1.0 - numeric_distance

        results.append(
            SearchHit(
                code_chunk=code_chunk,
                distance=numeric_distance,
                similarity=similarity,
            )
        )

    return results

def search_code_chunks_hybrid(
    db: Session,
    project_id: int,
    query: str,
    top_k: int = 5,
) -> list[SearchHit]:
    """벡터 검색과 코드 키워드를 결합해 검색한다."""

    # 최종 Top-K보다 더 많은 후보를 먼저 벡터 검색한다.
    candidate_k = min(
        max(top_k * 5, 20),
        100,
    )

    vector_candidates = search_code_chunks(
        db=db,
        project_id=project_id,
        query=query,
        top_k=candidate_k,
    )

    signals = extract_query_signals(query)

    hybrid_hits: list[SearchHit] = []

    for candidate in vector_candidates:
        chunk = candidate.code_chunk

        lexical_scores = calculate_lexical_scores(
            signals=signals,
            file_path=chunk.file_path,
            content=chunk.content,
        )

        hybrid_score = calculate_hybrid_score(
            vector_similarity=candidate.similarity,
            filename_score=(
                lexical_scores.filename_score
            ),
            keyword_score=(
                lexical_scores.keyword_score
            ),
        )

        hybrid_hits.append(
            SearchHit(
                code_chunk=chunk,
                distance=candidate.distance,
                similarity=candidate.similarity,
                filename_score=(
                    lexical_scores.filename_score
                ),
                keyword_score=(
                    lexical_scores.keyword_score
                ),
                hybrid_score=hybrid_score,
            )
        )

    hybrid_hits.sort(
        key=lambda hit: (
            hit.hybrid_score
            if hit.hybrid_score is not None
            else 0.0
        ),
        reverse=True,
    )

    return hybrid_hits[:top_k]