import pytest

from app.services.code_chunker import split_source_code


def test_empty_source_returns_empty_list() -> None:
    chunks = split_source_code("")

    assert chunks == []


def test_short_source_creates_single_chunk() -> None:
    content = "\n".join(
        f"line {i}"
        for i in range(1, 51)
    )

    chunks = split_source_code(
        content=content,
        max_lines=100,
        overlap_lines=20,
    )

    assert len(chunks) == 1

    assert chunks[0].chunk_index == 0
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 50


def test_long_source_creates_overlapping_chunks() -> None:
    content = "\n".join(
        f"line {i}"
        for i in range(1, 251)
    )

    chunks = split_source_code(
        content=content,
        max_lines=100,
        overlap_lines=20,
    )

    assert len(chunks) == 3

    assert chunks[0].chunk_index == 0
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 100

    assert chunks[1].chunk_index == 1
    assert chunks[1].start_line == 81
    assert chunks[1].end_line == 180

    assert chunks[2].chunk_index == 2
    assert chunks[2].start_line == 161
    assert chunks[2].end_line == 250


def test_exact_max_lines_creates_one_chunk() -> None:
    content = "\n".join(
        f"line {i}"
        for i in range(1, 101)
    )

    chunks = split_source_code(
        content=content,
        max_lines=100,
        overlap_lines=20,
    )

    assert len(chunks) == 1

    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 100


def test_overlap_must_be_less_than_max_lines() -> None:
    with pytest.raises(ValueError):
        split_source_code(
            content="test",
            max_lines=100,
            overlap_lines=100,
        )


def test_max_lines_must_be_positive() -> None:
    with pytest.raises(ValueError):
        split_source_code(
            content="test",
            max_lines=0,
            overlap_lines=0,
        )


def test_overlap_cannot_be_negative() -> None:
    with pytest.raises(ValueError):
        split_source_code(
            content="test",
            max_lines=100,
            overlap_lines=-1,
        )