"""Pomocné funkce diverzity a kompatibilní vstup do MMR výběru."""

from __future__ import annotations

from .mmr_selector import select_candidates_with_mmr
from .models import (
    AppConfig,
    CombinationCandidate,
    DiversitySelectionResult,
    NumberTuple,
)


def overlap_count(a: NumberTuple, b: NumberTuple) -> int:
    """Vrátí počet společných čísel dvou kombinací."""
    return len(frozenset(a) & frozenset(b))


def jaccard_similarity(a: NumberTuple, b: NumberTuple) -> float:
    """Vrátí Jaccardovu podobnost dvou kombinací."""
    set_a = frozenset(a)
    set_b = frozenset(b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def is_diverse_enough(
    candidate: CombinationCandidate,
    selected: list[CombinationCandidate],
    max_overlap: int,
) -> bool:
    """Zkontroluje absolutní limit překryvu s již vybraným portfoliem."""
    return all(overlap_count(candidate.numbers, item.numbers) <= max_overlap for item in selected)


def select_diverse_candidates_with_diagnostics(
    candidates: list[CombinationCandidate],
    config: AppConfig,
) -> DiversitySelectionResult:
    """Kompatibilní rozhraní delegující finální výběr na deterministické MMR."""
    return select_candidates_with_mmr(candidates, config)


def select_diverse_candidates(
    candidates: list[CombinationCandidate],
    config: AppConfig,
) -> list[CombinationCandidate]:
    """Kompatibilní varianta vracející pouze finální kandidáty."""
    return select_candidates_with_mmr(candidates, config).selected
