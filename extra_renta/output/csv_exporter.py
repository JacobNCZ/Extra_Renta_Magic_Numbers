"""CSV export finálních kandidátních kombinací."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from ..core.models import CombinationCandidate
from ..core.score_explainer import format_score_explanation
from .serialization import ensure_parent

CSV_FIELDNAMES = [
    "rank",
    "numbers",
    "score",
    "total_sum",
    "odd_count",
    "even_count",
    "low_count",
    "high_count",
    "span",
    "max_gap",
    "gap_std",
    "adjacent_pairs",
    "max_consecutive_run_length",
    "max_same_last_digit",
    "max_historical_overlap",
    "repeated_from_last_draw",
    "neighbors_of_last_draw",
    "score_components_json",
    "score_explanation",
    "mmr_marginal_gain",
    "mmr_normalized_score",
    "mmr_number_balance",
    "mmr_pair_coverage",
    "mmr_overlap_diversity",
    "mmr_pair_reuse_safety",
    "mmr_new_pairs",
    "mmr_max_pair_reuse_before",
]


def candidate_csv_rows(candidates: list[CombinationCandidate]) -> list[dict[str, object]]:
    """Vrátí kandidáty jako řádky vhodné pro CSV export i Streamlit."""
    rows: list[dict[str, object]] = []
    for rank, candidate in enumerate(candidates, start=1):
        metrics = candidate.metrics
        selection = candidate.selection
        rows.append({
            "rank": rank,
            "numbers": " ".join(str(number) for number in candidate.numbers),
            "score": candidate.score.total_score,
            "total_sum": metrics.total_sum,
            "odd_count": metrics.odd_count,
            "even_count": metrics.even_count,
            "low_count": metrics.low_count,
            "high_count": metrics.high_count,
            "span": metrics.span,
            "max_gap": metrics.max_gap,
            "gap_std": round(metrics.gap_std, 4),
            "adjacent_pairs": metrics.adjacent_pairs,
            "max_consecutive_run_length": metrics.max_consecutive_run_length,
            "max_same_last_digit": metrics.max_same_last_digit,
            "max_historical_overlap": metrics.max_historical_overlap,
            "repeated_from_last_draw": metrics.repeated_from_last_draw,
            "neighbors_of_last_draw": metrics.neighbors_of_last_draw,
            "score_components_json": json.dumps(dict(candidate.score.components), ensure_ascii=False),
            "score_explanation": format_score_explanation(candidate),
            "mmr_marginal_gain": selection.marginal_gain if selection else None,
            "mmr_normalized_score": selection.normalized_score if selection else None,
            "mmr_number_balance": selection.number_balance if selection else None,
            "mmr_pair_coverage": selection.pair_coverage if selection else None,
            "mmr_overlap_diversity": selection.overlap_diversity if selection else None,
            "mmr_pair_reuse_safety": selection.pair_reuse_safety if selection else None,
            "mmr_new_pairs": selection.new_pairs if selection else None,
            "mmr_max_pair_reuse_before": selection.max_pair_reuse_before if selection else None,
        })
    return rows


def candidates_to_csv_text(candidates: list[CombinationCandidate]) -> str:
    """Vrátí CSV export jako text bez zápisu na disk."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    writer.writerows(candidate_csv_rows(candidates))
    return buffer.getvalue()


def export_candidates_to_csv(candidates: list[CombinationCandidate], path: str | Path) -> None:
    """Uloží finální kandidáty do CSV pro rychlou kontrolu v Excelu."""
    output_path = ensure_parent(path)
    output_path.write_text(candidates_to_csv_text(candidates), encoding="utf-8", newline="")
