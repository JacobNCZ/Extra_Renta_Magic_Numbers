"""Konfigurační datové modely pro Extra Renta."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GeneratorConfig:
    """Nastavení generátoru kombinací."""

    number_min: int = 1
    number_max: int = 33
    pick_count: int = 7
    mode: str = "balanced"


@dataclass(frozen=True)
class HardFilterConfig:
    """Konfigurace tvrdých filtrů.

    Tvrdé filtry vrací pouze ANO/NE. Slouží ke zúžení prostoru kombinací,
    nikoli k predikci výhry.
    """

    sum_min: int = 90
    sum_max: int = 148
    allowed_odd_counts: tuple[int, ...] = (2, 3, 4, 5)
    low_range: tuple[int, int] = (1, 17)
    allowed_low_counts: tuple[int, ...] = (2, 3, 4, 5)
    tier_ranges: tuple[tuple[int, int], ...] = ((1, 11), (12, 22), (23, 33))
    min_non_empty_tiers: int = 2
    max_numbers_in_one_tier: int = 5
    bucket_ranges: tuple[tuple[int, int], ...] = ((1, 9), (10, 19), (20, 29), (30, 33))
    min_non_empty_buckets: int = 3
    max_numbers_in_one_bucket: int = 4
    min_span: int = 18
    max_span: int = 31
    max_single_gap: int = 18
    max_adjacent_pairs: int = 3
    max_consecutive_run_length: int = 3
    max_same_last_digit: int = 3
    exclude_exact_historical_draws: bool = True
    max_historical_overlap: int = 5


@dataclass(frozen=True)
class ScoringConfig:
    """Konfigurace měkkého skórování.

    Skóre označuje shodu s pravidly zvolené předvolby, nikoli vyšší
    pravděpodobnost výhry.
    """

    weights: Mapping[str, float] = field(default_factory=lambda: {
        "sum_balance": 15.0,
        "odd_even_balance": 10.0,
        "low_high_balance": 10.0,
        "tier_balance": 10.0,
        "bucket_balance": 10.0,
        "span_balance": 10.0,
        "gap_balance": 10.0,
        "historical_similarity": 10.0,
        "pattern_safety": 10.0,
        "overall_uniformity": 5.0,
    })
    min_score_to_keep: float = 70.0
    max_score: float = 100.0
    max_candidates_for_diversity: int = 100_000

    ideal_sum: float = 119.0
    preferred_odd_counts: tuple[int, ...] = (3, 4)
    preferred_low_counts: tuple[int, ...] = (3, 4)
    preferred_min_non_empty_tiers: int = 3
    preferred_min_non_empty_buckets: int = 4
    preferred_max_bucket_count: int = 3
    ideal_span_min: int = 22
    ideal_span_max: int = 29
    max_gap_for_full_score: int = 15
    gap_std_min: float = 1.4
    gap_std_max: float = 5.0
    gap_std_ideal_min: float = 1.7
    gap_std_ideal_max: float = 4.5

    adjacent_pairs_soft_limit: int = 2
    consecutive_run_soft_limit: int = 3
    same_last_digit_soft_limit: int = 3
    gap_std_pattern_min: float = 1.4
    repeated_from_last_draw_limit: int = 3
    neighbors_of_last_draw_limit: int = 4


@dataclass(frozen=True)
class DiversityConfig:
    """Tvrdé bezpečnostní limity finálního portfolia.

    ``max_output_count`` je pouze horní mez výstupu. Menší počet je platný
    výsledek, pokud už není k dispozici další přípustný kandidát.
    """

    max_output_count: int = 1_000
    max_overlap_between_selected: int = 4
    max_pair_reuse: int = 20
    max_triplet_reuse: int = 5
    enforce_pair_triplet_limits: bool = False


@dataclass(frozen=True)
class MMRConfig:
    """Nastavení deterministického marginal-gain greedy výběru.

    Všechny komponenty jsou normalizované do rozsahu 0–1. Váhy určují poměr
    individuálního skóre a přínosu kandidáta pro celé portfolio.
    """

    score_weight: float = 0.45
    number_balance_weight: float = 0.20
    pair_coverage_weight: float = 0.20
    overlap_diversity_weight: float = 0.10
    pair_reuse_safety_weight: float = 0.05
    min_marginal_gain: float = 0.0
    diversity_reserve_fraction: float = 0.20


@dataclass(frozen=True)
class ExportConfig:
    """Nastavení exportu výsledků a statistik běhu."""

    csv_path: str = "output/final_candidates.csv"
    json_path: str = "output/final_candidates.json"
    stats_path: str = "output/run_stats.json"
    html_report_path: str = "output/report.html"
    last_run_config_path: str = "output/last_run_config.json"


@dataclass(frozen=True)
class AppConfig:
    """Hlavní konfigurace aplikace."""

    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    filters: HardFilterConfig = field(default_factory=HardFilterConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    diversity: DiversityConfig = field(default_factory=DiversityConfig)
    mmr: MMRConfig = field(default_factory=MMRConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
