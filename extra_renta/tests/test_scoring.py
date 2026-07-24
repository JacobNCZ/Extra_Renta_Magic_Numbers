from extra_renta.config import DEFAULT_CONFIG
from extra_renta.core.scoring import score_combination
from extra_renta.core.statistics import build_historical_context, calculate_combination_metrics


def test_score_has_breakdown_and_range():
    ctx = build_historical_context([], DEFAULT_CONFIG)
    numbers = (4, 9, 13, 18, 22, 27, 31)
    metrics = calculate_combination_metrics(numbers, DEFAULT_CONFIG, ctx)
    score = score_combination(metrics, ctx, DEFAULT_CONFIG)
    assert 0 <= score.total_score <= 100
    assert "sum_balance" in score.components
    assert "historical_similarity" in score.components
