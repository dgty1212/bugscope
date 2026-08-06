import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkData:
    """DB에 저장하기 전 단계의 코드 조각."""

    chunk_index: int
    start_line: int
    end_line: int
    content: str
    content_hash: str


def split_source_code(
    content: str,
    max_lines: int = 100,
    overlap_lines: int = 20,
) -> list[ChunkData]:
    """소스코드를 줄 단위로 겹치게 분할한다."""

    if max_lines <= 0:
        raise ValueError("max_lines는 1 이상이어야 합니다.")

    if overlap_lines < 0:
        raise ValueError("overlap_lines는 0 이상이어야 합니다.")

    if overlap_lines >= max_lines:
        raise ValueError(
            "overlap_lines는 max_lines보다 작아야 합니다."
        )

    lines = content.splitlines()

    if not lines:
        return []

    chunks: list[ChunkData] = []

    step = max_lines - overlap_lines
    start_index = 0
    chunk_index = 0
    total_lines = len(lines)

    while start_index < total_lines:
        end_index = min(
            start_index + max_lines,
            total_lines,
        )

        chunk_lines = lines[start_index:end_index]
        chunk_content = "\n".join(chunk_lines)

        content_hash = hashlib.sha256(
            chunk_content.encode("utf-8")
        ).hexdigest()

        chunks.append(
            ChunkData(
                chunk_index=chunk_index,
                start_line=start_index + 1,
                end_line=end_index,
                content=chunk_content,
                content_hash=content_hash,
            )
        )

        # 마지막 줄까지 포함했다면 추가 조각을 만들지 않는다.
        if end_index == total_lines:
            break

        start_index += step
        chunk_index += 1

    return chunks