"""Lidsky čitelné vysvětlení skóre kandidátních kombinací."""

from __future__ import annotations

from .models import CombinationCandidate

COMPONENT_LABELS: dict[str, str] = {
    "sum_balance": "součet čísel",
    "odd_even_balance": "poměr sudá/lichá",
    "low_high_balance": "poměr nízká/vysoká",
    "tier_balance": "rozložení nízká/střední/vysoká",
    "bucket_balance": "rozložení do jemnějších pásem",
    "span_balance": "rozpětí kombinace",
    "gap_balance": "mezery mezi čísly",
    "historical_similarity": "historická podobnost",
    "pattern_safety": "odolnost vůči jednoduchým vzorům",
    "human_pattern_penalty": "odolnost vůči jednoduchým vzorům",
    "overall_uniformity": "celková rovnoměrnost",
}


def explain_score_components(candidate: CombinationCandidate) -> list[dict[str, object]]:
    """Vrátí strukturovaný, lidsky čitelný rozpad skóre."""
    return [
        {
            "key": key,
            "label": COMPONENT_LABELS.get(key, key),
            "points": float(value),
            "max_points": None,
        }
        for key, value in sorted(candidate.score.components.items())
    ]


def format_score_explanation(candidate: CombinationCandidate) -> str:
    """Vrátí jednověté vysvětlení skóre vhodné do CSV/konzole."""
    parts = [
        f"{item['label']}: {float(item['points']):.2f} bodů"
        for item in explain_score_components(candidate)
    ]
    return "; ".join(parts)
