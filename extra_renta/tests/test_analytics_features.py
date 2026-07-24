from dataclasses import replace

from extra_renta.core.filters import apply_hard_filters
from extra_renta.core.models import CombinationCandidate, RunStats
from extra_renta.core.score_explainer import format_score_explanation
from extra_renta.core.scoring import score_combination
from extra_renta.core.statistics import build_historical_context, calculate_combination_metrics
from extra_renta.main import SAMPLE_MODE, benchmark_run, run_quick_test
from extra_renta.output.exporter import export_html_report
from extra_renta.output.printer import evaluate_strictness
from extra_renta.presets import get_preset


def _candidate(numbers, config):
    context = build_historical_context([], config)
    metrics = calculate_combination_metrics(numbers, config, context)
    result = apply_hard_filters(numbers, metrics, context, config)
    score = score_combination(metrics, context, config)
    return CombinationCandidate(numbers, metrics, result, score)


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
            low_range=(1, 6),
            tier_ranges=((1, 4), (5, 8), (9, 12)),
            bucket_ranges=((1, 3), (4, 6), (7, 9), (10, 12)),
            max_historical_overlap=7,
        ),
        scoring=replace(cfg.scoring, min_score_to_keep=0, max_candidates_for_diversity=50, ideal_sum=45),
        diversity=replace(cfg.diversity, max_output_count=5, enforce_pair_triplet_limits=False),
    )
    return replace(preset, config=cfg)


def test_score_explanation_is_human_readable():
    config = get_preset("recommended").config
    candidate = _candidate((4, 9, 13, 18, 22, 27, 31), config)
    text = format_score_explanation(candidate)

    assert "součet čísel" in text
    assert "poměr sudá/lichá" in text


def test_historical_validation_detects_duplicate_date_and_combination():
    config = get_preset("recommended").config
    draws = [
        {"date": "2024-01-01", "numbers": [1, 2, 3, 4, 5, 6, 7]},
        {"date": "2024-01-01", "numbers": [1, 2, 3, 4, 5, 6, 7]},
        {"date": "bad-date", "numbers": [1, 2, 3]},
    ]
    context = build_historical_context(draws, config)

    assert "2024-01-01" in context.duplicate_dates
    assert (1, 2, 3, 4, 5, 6, 7) in context.duplicate_combinations
    assert "bad-date" in context.date_parse_errors
    assert len(context.invalid_draws) == 1


def test_html_report_uses_maximum_limit_and_mmr(tmp_path):
    preset = get_preset("recommended")
    config = preset.config
    context = build_historical_context([], config)
    candidate = _candidate((4, 9, 13, 18, 22, 27, 31), config)
    stats = RunStats(
        total_possible=10,
        generated=10,
        passed_hard_filters=5,
        passed_min_score=3,
        kept_for_diversity=1,
        final_selected=1,
    )
    path = tmp_path / "report.html"

    export_html_report([candidate], stats, context, path, preset_key=preset.key, preset_label=preset.label, config=config)

    report = path.read_text(encoding="utf-8")
    assert "Extra Renta · report po běhu" in report
    assert "Maximální limit" in report
    assert "MMR portfolio výběr" in report
    assert "Monte Carlo" not in report
    assert "@media print" in report


def test_quick_test_and_benchmark_return_sample_stats():
    preset = _tiny_preset()
    context = build_historical_context([], preset.config)

    quick_stats = run_quick_test(preset, context, sample_size=20, seed=1)
    bench_stats = benchmark_run(preset, context, sample_size=20)

    assert quick_stats.generation_mode == SAMPLE_MODE
    assert quick_stats.sample_size == 20
    assert bench_stats.benchmark.total_seconds > 0


def test_run_stats_filter_throughput_and_strictness_warnings():
    stats = RunStats(
        total_possible=100,
        generated=100,
        passed_hard_filters=10,
        passed_min_score=5,
        kept_for_diversity=5,
        final_selected=3,
    )
    stats.failed_by_filter = {"sum_range": 60, "odd_even_balance": 30}

    throughput = stats.filter_throughput(("sum_range", "odd_even_balance"))
    warnings = evaluate_strictness(stats, max_output_count=10)

    assert throughput[0]["passed_after_filter"] == 40
    assert throughput[1]["passed_after_filter"] == 10
    assert warnings
