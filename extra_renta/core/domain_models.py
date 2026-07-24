"""Doménové modely kombinací, filtrů, scoringu a finálního výběru."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .history_models import NumberTuple


@dataclass(frozen=True, slots=True)
class CombinationMetrics:
    """Metriky spočítané pro jednu kombinaci."""

    numbers: NumberTuple
    total_sum: int
    odd_count: int
    even_count: int
    low_count: int
    high_count: int
    tier_counts: tuple[int, ...]
    bucket_counts: tuple[int, ...]
    non_empty_tiers: int
    non_empty_buckets: int
    max_bucket_count: int
    span: int
    gaps: tuple[int, ...]
    max_gap: int
    gap_std: float
    adjacent_pairs: int
    max_consecutive_run_length: int
    max_same_last_digit: int
    max_historical_overlap: int
    repeated_from_last_draw: int
    neighbors_of_last_draw: int


@dataclass(frozen=True, slots=True)
class FilterResult:
    """Výsledek tvrdých filtrů."""

    passed: bool
    passed_filters: tuple[str, ...] = ()
    failed_filter: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Vysvětlitelný rozpad skóre."""

    total_score: float
    components: Mapping[str, float]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SelectionBreakdown:
    """Vysvětlení marginálního přínosu kandidáta pro portfolio."""

    marginal_gain: float
    normalized_score: float
    number_balance: float
    pair_coverage: float
    overlap_diversity: float
    pair_reuse_safety: float
    new_pairs: int
    max_pair_reuse_before: int


@dataclass(frozen=True, slots=True)
class CombinationCandidate:
    """Kandidát připravený k finálnímu portfolio výběru."""

    numbers: NumberTuple
    metrics: CombinationMetrics
    filter_result: FilterResult
    score: ScoreBreakdown
    selection: SelectionBreakdown | None = None
