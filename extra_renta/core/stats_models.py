"""Modely diagnostiky diverzifikace a statistik běhu."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .domain_models import CombinationCandidate


@dataclass
class DiversityDiagnostics:
    """Diagnostika finálního MMR výběru."""

    max_output_count: int = 0
    candidates_considered: int = 0
    selected_count: int = 0
    rejected_overlap: int = 0
    rejected_pair_reuse: int = 0
    rejected_triplet_reuse: int = 0
    stopped_after_reaching_limit: bool = False
    stop_reason: str = "not_started"
    selection_strategy: str = "mmr"
    mmr_candidate_evaluations: int = 0
    mmr_heap_recomputations: int = 0
    mmr_average_gain: float | None = None
    mmr_min_gain: float | None = None
    mmr_max_gain: float | None = None

    @property
    def rejected_total(self) -> int:
        return self.rejected_overlap + self.rejected_pair_reuse + self.rejected_triplet_reuse

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_output_count": self.max_output_count,
            "candidates_considered": self.candidates_considered,
            "selected_count": self.selected_count,
            "rejected_total": self.rejected_total,
            "rejected_overlap": self.rejected_overlap,
            "rejected_pair_reuse": self.rejected_pair_reuse,
            "rejected_triplet_reuse": self.rejected_triplet_reuse,
            "stopped_after_reaching_limit": self.stopped_after_reaching_limit,
            "stop_reason": self.stop_reason,
            "selection_strategy": self.selection_strategy,
            "mmr_candidate_evaluations": self.mmr_candidate_evaluations,
            "mmr_heap_recomputations": self.mmr_heap_recomputations,
            "mmr_average_gain": self.mmr_average_gain,
            "mmr_min_gain": self.mmr_min_gain,
            "mmr_max_gain": self.mmr_max_gain,
        }


@dataclass(frozen=True)
class DiversitySelectionResult:
    """Výsledek diverzifikace včetně diagnostiky."""

    selected: list[CombinationCandidate]
    diagnostics: DiversityDiagnostics


@dataclass
class BenchmarkStats:
    """Jednoduchý benchmark výkonu jedné pipeline."""

    total_seconds: float = 0.0
    generation_filter_scoring_seconds: float = 0.0
    selection_seconds: float = 0.0
    export_seconds: float = 0.0
    combinations_per_second: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "total_seconds": round(self.total_seconds, 6),
            "generation_filter_scoring_seconds": round(self.generation_filter_scoring_seconds, 6),
            "selection_seconds": round(self.selection_seconds, 6),
            "export_seconds": round(self.export_seconds, 6),
            "combinations_per_second": round(self.combinations_per_second, 3),
        }


@dataclass
class RunStats:
    """Statistika běhu programu a zúžení prostoru kombinací."""

    total_possible: int = 0
    generated: int = 0
    passed_hard_filters: int = 0
    passed_min_score: int = 0
    kept_for_diversity: int = 0
    final_selected: int = 0
    invalid_historical_rows: int = 0
    generation_mode: str = "full"
    sample_size: int | None = None
    random_seed: int | None = None
    failed_by_filter: dict[str, int] = field(default_factory=dict)
    strictness_warnings: tuple[str, ...] = ()
    diversity_diagnostics: DiversityDiagnostics = field(default_factory=DiversityDiagnostics)
    benchmark: BenchmarkStats = field(default_factory=BenchmarkStats)

    def add_filter_failure(self, filter_name: str) -> None:
        self.failed_by_filter[filter_name] = self.failed_by_filter.get(filter_name, 0) + 1

    def narrowing_ratio(self) -> float:
        if self.total_possible == 0:
            return 0.0
        return self.final_selected / self.total_possible

    def percent_of_total(self, value: int) -> float:
        if self.total_possible == 0:
            return 0.0
        return (value / self.total_possible) * 100

    def percent_of_generated(self, value: int) -> float:
        if self.generated == 0:
            return 0.0
        return (value / self.generated) * 100

    def filter_throughput(self, filter_order: tuple[str, ...]) -> list[dict[str, Any]]:
        remaining = self.generated
        rows: list[dict[str, Any]] = []
        known = set(filter_order)
        for filter_name in filter_order:
            rejected = self.failed_by_filter.get(filter_name, 0)
            remaining -= rejected
            rows.append({
                "filter": filter_name,
                "rejected": rejected,
                "passed_after_filter": max(remaining, 0),
                "passed_after_filter_pct_of_generated": self.percent_of_generated(max(remaining, 0)),
            })

        extra_rejected = sum(count for name, count in self.failed_by_filter.items() if name not in known)
        if extra_rejected:
            remaining -= extra_rejected
            rows.append({
                "filter": "other",
                "rejected": extra_rejected,
                "passed_after_filter": max(remaining, 0),
                "passed_after_filter_pct_of_generated": self.percent_of_generated(max(remaining, 0)),
            })
        return rows

    def candidate_cap_reached(self) -> bool:
        return self.passed_min_score > self.kept_for_diversity

    def output_limit_reached(self, max_output_count: int) -> bool:
        return self.final_selected >= max_output_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_mode": self.generation_mode,
            "sample_size": self.sample_size,
            "random_seed": self.random_seed,
            "total_possible": self.total_possible,
            "generated": self.generated,
            "passed_hard_filters": self.passed_hard_filters,
            "passed_min_score": self.passed_min_score,
            "kept_for_diversity": self.kept_for_diversity,
            "final_selected": self.final_selected,
            "invalid_historical_rows": self.invalid_historical_rows,
            "failed_by_filter": self.failed_by_filter,
            "strictness_warnings": list(self.strictness_warnings),
            "diversity_diagnostics": self.diversity_diagnostics.to_dict(),
            "benchmark": self.benchmark.to_dict(),
            "candidate_cap_reached": self.candidate_cap_reached(),
            "narrowing_ratio": self.narrowing_ratio(),
            "percentages_of_total": {
                "generated": self.percent_of_total(self.generated),
                "passed_hard_filters": self.percent_of_total(self.passed_hard_filters),
                "passed_min_score": self.percent_of_total(self.passed_min_score),
                "kept_for_diversity": self.percent_of_total(self.kept_for_diversity),
                "final_selected": self.percent_of_total(self.final_selected),
            },
            "percentages_of_generated": {
                "passed_hard_filters": self.percent_of_generated(self.passed_hard_filters),
                "passed_min_score": self.percent_of_generated(self.passed_min_score),
                "kept_for_diversity": self.percent_of_generated(self.kept_for_diversity),
                "final_selected": self.percent_of_generated(self.final_selected),
            },
        }
