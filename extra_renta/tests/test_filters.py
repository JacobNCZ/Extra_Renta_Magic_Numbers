from extra_renta.config import DEFAULT_CONFIG
from extra_renta.core.filters import apply_hard_filters
from extra_renta.core.statistics import build_historical_context, calculate_combination_metrics


def _context():
    return build_historical_context([
        {"date": "2024-01-01", "numbers": [3, 8, 12, 17, 21, 26, 32]},
    ], DEFAULT_CONFIG)


def test_filter_rejects_extreme_sum():
    ctx = _context()
    numbers = (1, 2, 3, 4, 5, 6, 7)
    metrics = calculate_combination_metrics(numbers, DEFAULT_CONFIG, ctx)
    result = apply_hard_filters(numbers, metrics, ctx, DEFAULT_CONFIG)
    assert not result.passed
    assert result.failed_filter == "sum_range"


def test_filter_rejects_exact_historical_draw():
    ctx = _context()
    numbers = (3, 8, 12, 17, 21, 26, 32)
    metrics = calculate_combination_metrics(numbers, DEFAULT_CONFIG, ctx)
    result = apply_hard_filters(numbers, metrics, ctx, DEFAULT_CONFIG)
    assert not result.passed
    assert result.failed_filter == "exact_historical_draw"


def test_filter_accepts_balanced_candidate():
    ctx = _context()
    numbers = (4, 9, 13, 18, 22, 27, 31)
    metrics = calculate_combination_metrics(numbers, DEFAULT_CONFIG, ctx)
    result = apply_hard_filters(numbers, metrics, ctx, DEFAULT_CONFIG)
    assert result.passed


def test_filter_passed_names_use_consecutive_run_key():
    ctx = _context()
    numbers = (4, 9, 13, 18, 22, 27, 31)
    metrics = calculate_combination_metrics(numbers, DEFAULT_CONFIG, ctx)
    result = apply_hard_filters(numbers, metrics, ctx, DEFAULT_CONFIG)

    assert result.passed
    assert "consecutive_run" in result.passed_filters
    assert "consecutive_numbers" not in result.passed_filters
