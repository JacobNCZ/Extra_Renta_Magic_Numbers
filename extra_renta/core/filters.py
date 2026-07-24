"""Tvrdé filtry pro kombinace.

Každý filtr slouží pouze jako praktické zúžení prostoru kombinací. Historické
kontroly jsou oddělené od strukturálních filtrů, aby se stejné kontroly nemusely
spouštět dvakrát.
"""

from __future__ import annotations

from .models import AppConfig, CombinationMetrics, FilterResult, HistoricalContext, NumberTuple

_BASE_NOTE = "Tvrdé filtry jsou praktické zúžení prostoru, nikoli predikce výhry."


def _fail(name: str, passed_filters: list[str], notes: list[str]) -> FilterResult:
    return FilterResult(
        passed=False,
        passed_filters=tuple(passed_filters),
        failed_filter=name,
        notes=tuple(notes),
    )


def apply_structural_filters(
    numbers: NumberTuple,
    metrics: CombinationMetrics,
    config: AppConfig,
) -> FilterResult:
    """Aplikuje nehistorické tvrdé filtry právě jednou."""
    gen = config.generator
    cfg = config.filters
    passed: list[str] = []
    notes: list[str] = [_BASE_NOTE]

    if len(numbers) != gen.pick_count:
        return _fail("basic_length", passed, notes)
    passed.append("basic_length")

    if len(set(numbers)) != gen.pick_count:
        return _fail("unique_numbers", passed, notes)
    passed.append("unique_numbers")

    if any(number < gen.number_min or number > gen.number_max for number in numbers):
        return _fail("number_range", passed, notes)
    passed.append("number_range")

    if not (cfg.sum_min <= metrics.total_sum <= cfg.sum_max):
        return _fail("sum_range", passed, notes)
    passed.append("sum_range")

    if metrics.odd_count not in cfg.allowed_odd_counts:
        return _fail("odd_even_balance", passed, notes)
    passed.append("odd_even_balance")

    if metrics.low_count not in cfg.allowed_low_counts:
        return _fail("low_high_balance", passed, notes)
    passed.append("low_high_balance")

    if metrics.non_empty_tiers < cfg.min_non_empty_tiers:
        return _fail("tier_distribution", passed, notes)
    if max(metrics.tier_counts, default=0) > cfg.max_numbers_in_one_tier:
        return _fail("tier_concentration", passed, notes)
    passed.append("tier_distribution")

    if metrics.non_empty_buckets < cfg.min_non_empty_buckets:
        return _fail("bucket_distribution", passed, notes)
    if metrics.max_bucket_count > cfg.max_numbers_in_one_bucket:
        return _fail("bucket_concentration", passed, notes)
    passed.append("bucket_distribution")

    if not (cfg.min_span <= metrics.span <= cfg.max_span):
        return _fail("span_range", passed, notes)
    passed.append("span_range")

    if metrics.max_gap > cfg.max_single_gap:
        return _fail("max_gap", passed, notes)
    passed.append("max_gap")

    if metrics.adjacent_pairs > cfg.max_adjacent_pairs:
        return _fail("adjacent_pairs", passed, notes)
    if metrics.max_consecutive_run_length > cfg.max_consecutive_run_length:
        return _fail("consecutive_run", passed, notes)
    passed.append("consecutive_run")

    if metrics.max_same_last_digit > cfg.max_same_last_digit:
        return _fail("last_digit_concentration", passed, notes)
    passed.append("last_digit_concentration")

    return FilterResult(
        passed=True,
        passed_filters=tuple(passed),
        failed_filter=None,
        notes=tuple(notes),
    )


def apply_historical_filters(
    numbers: NumberTuple,
    metrics: CombinationMetrics,
    historical_context: HistoricalContext,
    config: AppConfig,
) -> FilterResult:
    """Aplikuje pouze historické tvrdé kontroly."""
    cfg = config.filters
    passed: list[str] = []
    notes: list[str] = [
        "Historická data slouží pouze k omezení kopírování historie, nikoli k predikci."
    ]

    if cfg.exclude_exact_historical_draws and numbers in historical_context.exact_combinations:
        return _fail("exact_historical_draw", passed, notes)
    passed.append("exact_historical_draw")

    if metrics.max_historical_overlap > cfg.max_historical_overlap:
        return _fail("historical_overlap", passed, notes)
    passed.append("historical_overlap")

    return FilterResult(
        passed=True,
        passed_filters=tuple(passed),
        failed_filter=None,
        notes=tuple(notes),
    )


def merge_filter_results(structural: FilterResult, historical: FilterResult) -> FilterResult:
    """Sloučí úspěšný strukturální výsledek s historickým výsledkem."""
    if not structural.passed:
        return structural
    return FilterResult(
        passed=historical.passed,
        passed_filters=structural.passed_filters + historical.passed_filters,
        failed_filter=historical.failed_filter,
        notes=structural.notes + historical.notes,
    )


def apply_hard_filters(
    numbers: NumberTuple,
    metrics: CombinationMetrics,
    historical_context: HistoricalContext,
    config: AppConfig,
    *,
    include_historical_checks: bool = True,
) -> FilterResult:
    """Kompatibilní fasáda nad nově rozdělenými filtry."""
    structural = apply_structural_filters(numbers, metrics, config)
    if not structural.passed or not include_historical_checks:
        return structural
    historical = apply_historical_filters(numbers, metrics, historical_context, config)
    return merge_filter_results(structural, historical)
