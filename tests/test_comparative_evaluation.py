from app.services.evaluation_service import (
    CaseRetrievalEvaluation,
    calculate_mode_metrics,
)


def test_calculate_mode_metrics() -> None:
    results = [
        CaseRetrievalEvaluation(
            file_rank=1,
            symbol_rank=1,
            has_expected_symbol=True,
            context_count=5,
        ),
        CaseRetrievalEvaluation(
            file_rank=2,
            symbol_rank=3,
            has_expected_symbol=True,
            context_count=5,
        ),
        CaseRetrievalEvaluation(
            file_rank=None,
            symbol_rank=None,
            has_expected_symbol=True,
            context_count=5,
        ),
    ]

    metrics = calculate_mode_metrics(
        results
    )

    assert metrics.evaluated_cases == 3
    assert metrics.symbol_cases == 3

    assert metrics.file_top1 == 1 / 3
    assert metrics.file_top3 == 2 / 3
    assert metrics.file_top5 == 2 / 3

    assert metrics.symbol_top1 == 1 / 3
    assert metrics.symbol_top3 == 2 / 3
    assert metrics.symbol_top5 == 2 / 3