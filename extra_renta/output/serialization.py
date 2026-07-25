"""Serializace kandidátů, metrik, skóre a konfigurace pro exporty."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..core.models import (
    AppConfig,
    CombinationCandidate,
    CombinationMetrics,
    ScoreBreakdown,
)
from ..core.score_explainer import explain_score_components, format_score_explanation

HARD_FILTER_EXPORT_ORDER: tuple[str, ...] = (
    "basic_length",
    "unique_numbers",
    "number_range",
    "sum_range",
    "odd_even_balance",
    "low_high_balance",
    "tier_distribution",
    "tier_concentration",
    "bucket_distribution",
    "bucket_concentration",
    "span_range",
    "max_gap",
    "adjacent_pairs",
    "consecutive_run",
    "last_digit_concentration",
    "exact_historical_draw",
    "historical_overlap",
)

FILTER_EXPORT_LABELS: dict[str, str] = {
    "basic_length": "Správný počet čísel",
    "unique_numbers": "Unikátnost čísel",
    "number_range": "Rozsah čísel",
    "sum_range": "Součet čísel",
    "odd_even_balance": "Sudá / lichá",
    "low_high_balance": "Nízká / vysoká",
    "tier_distribution": "Nízká/střední/vysoká pásma",
    "tier_concentration": "Koncentrace v pásmu",
    "bucket_distribution": "Rozložení do jemnějších pásem",
    "bucket_concentration": "Koncentrace v jemném pásmu",
    "span_range": "Rozpětí kombinace",
    "max_gap": "Maximální mezera",
    "adjacent_pairs": "Sousední dvojice",
    "consecutive_run": "Souvislá sekvence",
    "last_digit_concentration": "Stejná koncovka",
    "exact_historical_draw": "Přesný historický tah",
    "historical_overlap": "Historický překryv",
    "other": "Ostatní",
}


def ensure_parent(path: str | Path) -> Path:
    """Vytvoří cílovou složku exportu a vrátí normalizovanou cestu."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def format_int(value: int | float) -> str:
    """Formátuje čísla s mezerou jako oddělovačem tisíců."""
    return f"{int(value):,}".replace(",", " ")


def metrics_to_dict(metrics: CombinationMetrics) -> dict[str, Any]:
    """Převede metriky kandidáta na JSON serializovatelný slovník."""
    return {
        "numbers": list(metrics.numbers),
        "total_sum": metrics.total_sum,
        "odd_count": metrics.odd_count,
        "even_count": metrics.even_count,
        "low_count": metrics.low_count,
        "high_count": metrics.high_count,
        "tier_counts": list(metrics.tier_counts),
        "bucket_counts": list(metrics.bucket_counts),
        "non_empty_tiers": metrics.non_empty_tiers,
        "non_empty_buckets": metrics.non_empty_buckets,
        "max_bucket_count": metrics.max_bucket_count,
        "span": metrics.span,
        "gaps": list(metrics.gaps),
        "max_gap": metrics.max_gap,
        "gap_std": metrics.gap_std,
        "adjacent_pairs": metrics.adjacent_pairs,
        "max_consecutive_run_length": metrics.max_consecutive_run_length,
        "max_same_last_digit": metrics.max_same_last_digit,
        "max_historical_overlap": metrics.max_historical_overlap,
        "repeated_from_last_draw": metrics.repeated_from_last_draw,
        "neighbors_of_last_draw": metrics.neighbors_of_last_draw,
    }


def score_max_points(config: AppConfig | None) -> dict[str, float]:
    """Vrátí maximální body scoringových komponent pro export."""
    if config is None:
        return {}
    weights = {key: float(value) for key, value in config.scoring.weights.items()}
    if "pattern_safety" not in weights and "human_pattern_penalty" in weights:
        weights["pattern_safety"] = weights["human_pattern_penalty"]
    return weights


def score_to_dict(score: ScoreBreakdown, config: AppConfig | None = None) -> dict[str, Any]:
    """Převede rozpad skóre na JSON serializovatelný slovník."""
    return {
        "total_score": score.total_score,
        "components": dict(score.components),
        "component_max_points": score_max_points(config),
        "notes": list(score.notes),
    }


def selection_to_dict(candidate: CombinationCandidate) -> dict[str, Any] | None:
    """Převede MMR vysvětlení kandidáta na exportní slovník."""
    selection = candidate.selection
    if selection is None:
        return None
    return {
        "marginal_gain": selection.marginal_gain,
        "normalized_score": selection.normalized_score,
        "number_balance": selection.number_balance,
        "pair_coverage": selection.pair_coverage,
        "overlap_diversity": selection.overlap_diversity,
        "pair_reuse_safety": selection.pair_reuse_safety,
        "new_pairs": selection.new_pairs,
        "max_pair_reuse_before": selection.max_pair_reuse_before,
    }


def candidate_to_dict(candidate: CombinationCandidate, rank: int, config: AppConfig | None = None) -> dict[str, Any]:
    """Převede kandidáta na kompletní exportní záznam."""
    max_points = score_max_points(config)
    explanation = explain_score_components(candidate)
    if max_points:
        explanation = [
            {**item, "max_points": max_points.get(str(item["key"]))}
            for item in explanation
        ]
    return {
        "rank": rank,
        "numbers": list(candidate.numbers),
        "score": score_to_dict(candidate.score, config),
        "score_explanation": explanation,
        "score_explanation_text": format_score_explanation(candidate),
        "metrics": metrics_to_dict(candidate.metrics),
        "selection": selection_to_dict(candidate),
        "filter_result": {
            "passed": candidate.filter_result.passed,
            "passed_filters": list(candidate.filter_result.passed_filters),
            "failed_filter": candidate.filter_result.failed_filter,
            "notes": list(candidate.filter_result.notes),
        },
    }


def _jsonable(value: Any) -> Any:
    """Převede konfiguraci na stabilní JSON-kompatibilní strukturu."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def config_to_dict(config: AppConfig) -> dict[str, Any]:
    """Vrátí úplný snapshot konfigurace použité při běhu."""
    payload = _jsonable(asdict(config))
    payload["selection"] = {
        "strategy": "mmr",
        "algorithm_version": "1.0",
        "max_output_semantics": "upper_limit_not_guaranteed_target",
    }
    return payload
