from dataclasses import replace

import extra_renta.candidate_pool as candidate_pool_module
from extra_renta.candidate_pool import FULL_MODE, build_candidate_pool
from extra_renta.core.combination_generator import total_combination_count
from extra_renta.core.models import RunStats
from extra_renta.core.statistics import build_historical_context
from extra_renta.presets import get_preset


def _tiny_preset():
    preset = get_preset("recommended")
    cfg = preset.config
    cfg = replace(
        cfg,
        generator=replace(cfg.generator, number_min=1, number_max=12, pick_count=7),
        filters=replace(
            cfg.filters,
            sum_min=28,
            sum_max=63,
            allowed_odd_counts=tuple(range(8)),
            low_range=(1, 6),
            allowed_low_counts=tuple(range(8)),
            tier_ranges=((1, 4), (5, 8), (9, 12)),
            min_non_empty_tiers=1,
            max_numbers_in_one_tier=7,
            bucket_ranges=((1, 3), (4, 6), (7, 9), (10, 12)),
            min_non_empty_buckets=1,
            max_numbers_in_one_bucket=7,
            min_span=0,
            max_span=11,
            max_single_gap=11,
            max_adjacent_pairs=6,
            max_consecutive_run_length=7,
            max_same_last_digit=7,
            exclude_exact_historical_draws=False,
            max_historical_overlap=7,
        ),
        scoring=replace(
            cfg.scoring,
            min_score_to_keep=0,
            max_candidates_for_diversity=100,
            ideal_sum=45,
        ),
        diversity=replace(cfg.diversity, max_output_count=10, max_overlap_between_selected=6),
    )
    return replace(preset, config=cfg)


def test_candidate_pool_calculates_base_metrics_once_per_combination(monkeypatch):
    preset = _tiny_preset()
    context = build_historical_context([], preset.config)
    total = total_combination_count(preset.config.generator)
    stats = RunStats(total_possible=total, generation_mode=FULL_MODE)

    original = candidate_pool_module.calculate_combination_metrics
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(candidate_pool_module, "calculate_combination_metrics", counted)
    result = build_candidate_pool(
        preset,
        context,
        generation_mode=FULL_MODE,
        sample_size=total,
        seed=None,
        stats=stats,
        log_progress=False,
    )

    assert stats.generated == total
    assert calls == total
    assert result.candidates


def test_incremental_historical_overlap_matches_full_metric_calculation():
    from extra_renta.core.statistics import add_historical_overlap, calculate_combination_metrics

    preset = get_preset("recommended")
    context = build_historical_context(
        [
            {"date": "2024-01-01", "numbers": [4, 9, 13, 18, 22, 27, 31]},
            {"date": "2024-01-08", "numbers": [1, 6, 12, 17, 23, 29, 33]},
        ],
        preset.config,
    )
    numbers = (4, 9, 13, 18, 22, 28, 32)

    full = calculate_combination_metrics(
        numbers,
        preset.config,
        context,
        include_historical_overlap=True,
    )
    base = calculate_combination_metrics(
        numbers,
        preset.config,
        context,
        include_historical_overlap=False,
    )
    incremental = add_historical_overlap(base, context)

    assert incremental == full
