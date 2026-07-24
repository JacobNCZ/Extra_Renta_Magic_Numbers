from extra_renta.config import DEFAULT_CONFIG
from extra_renta.core.diversity import (
    jaccard_similarity,
    overlap_count,
    select_diverse_candidates,
    select_diverse_candidates_with_diagnostics,
)
from extra_renta.core.filters import apply_hard_filters
from extra_renta.core.models import CombinationCandidate
from extra_renta.core.scoring import score_combination
from extra_renta.core.statistics import build_historical_context, calculate_combination_metrics


def _candidate(numbers):
    ctx = build_historical_context([], DEFAULT_CONFIG)
    metrics = calculate_combination_metrics(numbers, DEFAULT_CONFIG, ctx)
    result = apply_hard_filters(numbers, metrics, ctx, DEFAULT_CONFIG)
    score = score_combination(metrics, ctx, DEFAULT_CONFIG)
    return CombinationCandidate(numbers, metrics, result, score)


def test_overlap_and_jaccard():
    a = (1, 2, 3, 10, 15, 20, 30)
    b = (1, 2, 3, 11, 16, 21, 31)
    assert overlap_count(a, b) == 3
    assert 0 < jaccard_similarity(a, b) < 1


def test_select_diverse_candidates_limits_overlap():
    candidates = [
        _candidate((4, 9, 13, 18, 22, 27, 31)),
        _candidate((4, 9, 13, 18, 22, 28, 32)),  # sdílí 5 čísel s prvním
        _candidate((1, 6, 12, 17, 23, 29, 33)),
    ]
    selected = select_diverse_candidates(candidates, DEFAULT_CONFIG)
    selected_numbers = {candidate.numbers for candidate in selected}
    assert candidates[0].numbers in selected_numbers
    assert candidates[1].numbers not in selected_numbers
    assert candidates[2].numbers in selected_numbers


def test_select_diverse_candidates_returns_diagnostics():
    candidates = [
        _candidate((4, 9, 13, 18, 22, 27, 31)),
        _candidate((4, 9, 13, 18, 22, 28, 32)),
        _candidate((1, 6, 12, 17, 23, 29, 33)),
    ]
    result = select_diverse_candidates_with_diagnostics(candidates, DEFAULT_CONFIG)

    assert result.diagnostics.candidates_considered >= len(result.selected)
    assert result.diagnostics.selected_count == len(result.selected)
    assert result.diagnostics.rejected_overlap >= 1
