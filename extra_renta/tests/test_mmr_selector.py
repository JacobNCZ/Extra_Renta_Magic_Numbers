from dataclasses import replace

from extra_renta.core.filters import apply_hard_filters
from extra_renta.core.mmr_selector import select_candidates_with_mmr
from extra_renta.core.models import CombinationCandidate
from extra_renta.core.scoring import score_combination
from extra_renta.core.statistics import build_historical_context, calculate_combination_metrics
from extra_renta.presets import get_preset


def _candidate(numbers, config):
    context = build_historical_context([], config)
    metrics = calculate_combination_metrics(numbers, config, context)
    filter_result = apply_hard_filters(numbers, metrics, context, config)
    score = score_combination(metrics, context, config)
    return CombinationCandidate(numbers, metrics, filter_result, score)


def test_mmr_is_deterministic_and_respects_maximum_limit():
    base = get_preset("recommended").config
    config = replace(
        base,
        diversity=replace(base.diversity, max_output_count=3, max_overlap_between_selected=4),
    )
    candidates = [
        _candidate((4, 9, 13, 18, 22, 27, 31), config),
        _candidate((4, 9, 13, 18, 22, 28, 32), config),
        _candidate((1, 6, 12, 17, 23, 29, 33), config),
        _candidate((2, 7, 11, 16, 21, 26, 30), config),
        _candidate((3, 8, 14, 19, 24, 28, 33), config),
    ]

    first = select_candidates_with_mmr(candidates, config)
    second = select_candidates_with_mmr(candidates, config)

    assert [item.numbers for item in first.selected] == [item.numbers for item in second.selected]
    assert len(first.selected) <= config.diversity.max_output_count
    assert first.diagnostics.selection_strategy == "mmr"
    assert all(item.selection is not None for item in first.selected)


def test_mmr_hard_overlap_guard_remains_enforced():
    base = get_preset("recommended").config
    config = replace(
        base,
        diversity=replace(base.diversity, max_output_count=3, max_overlap_between_selected=4),
    )
    similar_a = _candidate((4, 9, 13, 18, 22, 27, 31), config)
    similar_b = _candidate((4, 9, 13, 18, 22, 28, 32), config)
    different = _candidate((1, 6, 12, 17, 23, 29, 33), config)

    result = select_candidates_with_mmr([similar_a, similar_b, different], config)
    selected_numbers = {item.numbers for item in result.selected}

    assert not ({similar_a.numbers, similar_b.numbers} <= selected_numbers)
    assert different.numbers in selected_numbers
    assert result.diagnostics.rejected_overlap >= 1


def test_mmr_smaller_output_than_limit_is_valid():
    base = get_preset("recommended").config
    config = replace(base, diversity=replace(base.diversity, max_output_count=10))
    candidates = [_candidate((4, 9, 13, 18, 22, 27, 31), config)]

    result = select_candidates_with_mmr(candidates, config)

    assert len(result.selected) == 1
    assert not result.diagnostics.stopped_after_reaching_limit
    assert result.diagnostics.stop_reason in {"candidate_pool_exhausted", "no_feasible_candidate"}


def test_mmr_components_are_normalized():
    config = get_preset("recommended").config
    candidate = _candidate((4, 9, 13, 18, 22, 27, 31), config)

    result = select_candidates_with_mmr([candidate], config)
    breakdown = result.selected[0].selection

    assert breakdown is not None
    assert 0.0 <= breakdown.marginal_gain <= 1.0
    assert 0.0 <= breakdown.normalized_score <= 1.0
    assert 0.0 <= breakdown.number_balance <= 1.0
    assert 0.0 <= breakdown.pair_coverage <= 1.0
    assert breakdown.new_pairs == 21
