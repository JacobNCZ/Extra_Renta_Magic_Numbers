"""Kontrola vlastní uživatelské kombinace proti pravidlům běhu."""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Collection

from .core.filters import apply_hard_filters
from .core.models import (
    AppConfig,
    CombinationCandidate,
    CombinationMetrics,
    FilterResult,
    HistoricalContext,
    NumberTuple,
    ScoreBreakdown,
)
from .core.scoring import score_combination
from .core.statistics import calculate_combination_metrics

FILTER_LABELS: dict[str, str] = {
    "basic_length": "správný počet čísel",
    "unique_numbers": "unikátnost čísel",
    "number_range": "rozsah čísel",
    "sum_range": "součet čísel",
    "odd_even_balance": "sudá / lichá",
    "low_high_balance": "nízká / vysoká",
    "tier_distribution": "nízká/střední/vysoká pásma",
    "tier_concentration": "koncentrace v pásmu",
    "bucket_distribution": "rozložení do jemnějších pásem",
    "bucket_concentration": "koncentrace v jemném pásmu",
    "span_range": "rozpětí kombinace",
    "max_gap": "maximální mezera",
    "adjacent_pairs": "sousední dvojice",
    "consecutive_run": "souvislá sekvence",
    "last_digit_concentration": "stejná koncovka",
    "exact_historical_draw": "přesný historický tah",
    "historical_overlap": "historický překryv",
}


def _filter_label(name: str | None) -> str:
    if not name:
        return "neznámý filtr"
    return FILTER_LABELS.get(name, name)


@dataclass(frozen=True)
class CombinationCheckResult:
    """Výsledek kontroly jedné vlastní kombinace."""

    raw_input: str
    numbers: NumberTuple
    input_errors: tuple[str, ...]
    metrics: CombinationMetrics | None = None
    filter_result: FilterResult | None = None
    score: ScoreBreakdown | None = None
    passes_min_score: bool = False
    candidate_pool_membership_known: bool = True
    in_candidate_pool: bool = False
    candidate_pool_rank: int | None = None
    in_final_selection: bool = False
    final_rank: int | None = None
    closest_selected_overlap: int | None = None
    reason: str = ""

    @property
    def is_valid_input(self) -> bool:
        """Vrátí True, pokud vstup splňuje základní tvar kombinace."""
        return not self.input_errors

    @property
    def hard_filters_passed(self) -> bool:
        """Vrátí True, pokud kombinace prošla tvrdými filtry."""
        return bool(self.filter_result and self.filter_result.passed)


def parse_combination_input(raw_value: str, config: AppConfig) -> tuple[NumberTuple, tuple[str, ...]]:
    """Převede textový vstup uživatele na seřazenou kombinaci a validační chyby.

    Podporované zápisy:
    - ``1, 2, 3, 4, 5, 6, 7``
    - ``1 2 3 4 5 6 7``
    - ``[1, 2, 3, 4, 5, 6, 7]``
    - ``1;2;3;4;5;6;7``
    """
    gen = config.generator
    cleaned = raw_value.strip().translate(str.maketrans({char: " " for char in "[](){}"}))
    parts = [part for part in re.split(r"[,;\s]+", cleaned) if part]

    numbers: list[int] = []
    errors: list[str] = []
    for part in parts:
        try:
            numbers.append(int(part))
        except ValueError:
            errors.append(f"nečíselná hodnota: {part!r}")

    sorted_numbers = tuple(sorted(numbers))
    if len(sorted_numbers) != gen.pick_count:
        errors.append(f"očekáváno {gen.pick_count} čísel, zadáno {len(sorted_numbers)}")
    if len(set(sorted_numbers)) != len(sorted_numbers):
        errors.append("kombinace obsahuje duplicitní čísla")
    out_of_range = [number for number in sorted_numbers if number < gen.number_min or number > gen.number_max]
    if out_of_range:
        values = ", ".join(str(number) for number in out_of_range)
        errors.append(f"čísla mimo povolený rozsah {gen.number_min}–{gen.number_max}: {values}")

    return sorted_numbers, tuple(errors)


def _rank_lookup(candidates: list[CombinationCandidate]) -> dict[NumberTuple, int]:
    return {candidate.numbers: rank for rank, candidate in enumerate(candidates, start=1)}


def _closest_selected_overlap(numbers: NumberTuple, selected: list[CombinationCandidate]) -> int | None:
    if not selected:
        return None
    number_set = frozenset(numbers)
    return max(len(number_set & frozenset(candidate.numbers)) for candidate in selected)


def _build_reason(
    *,
    result: CombinationCheckResult,
    config: AppConfig,
    candidate_pool_cutoff: float | None,
) -> str:
    """Vrátí stručné vysvětlení výsledku kontroly."""
    if result.input_errors:
        return "Vstup nemá správný tvar kombinace, proto se nevyhodnocovaly filtry ani skóre."
    if result.filter_result and not result.filter_result.passed:
        return f"Kombinace neprošla tvrdým filtrem: {_filter_label(result.filter_result.failed_filter)}."
    if result.score and not result.passes_min_score:
        return (
            f"Kombinace prošla tvrdými filtry, ale skóre {result.score.total_score:.2f} "
            f"je pod minimem {config.scoring.min_score_to_keep:.2f}."
        )
    if result.in_final_selection:
        return "Kombinace je ve finálním diverzifikovaném výběru posledního běhu."
    if not result.candidate_pool_membership_known:
        return (
            "Kombinace prošla filtry a minimálním skóre. Členství v kandidátním poolu ale není "
            "pro tento běh uložené; ve finálním výběru posledního běhu se nenachází."
        )
    if not result.in_candidate_pool:
        cutoff = candidate_pool_cutoff
        if cutoff is None:
            return "Kombinace prošla pravidly, ale v uloženém kandidátním poolu posledního běhu není."
        if result.score and result.score.total_score >= cutoff:
            return (
                "Kombinace prošla filtry a minimálním skóre, ale v uloženém kandidátním poolu "
                "posledního běhu není. Její skóre je nad hranicí poolu; rozhodnout mohlo pořadí "
                "na hranici nebo diverzitní rezerva."
            )
        return (
            "Kombinace prošla filtry a minimálním skóre, ale nevešla se do užšího kandidátního poolu "
            f"omezeného na {config.scoring.max_candidates_for_diversity} kandidátů. "
            f"Nejnižší skóre v uloženém poolu je {cutoff:.2f}."
        )
    if result.closest_selected_overlap is not None and result.closest_selected_overlap > config.diversity.max_overlap_between_selected:
        return (
            "Kombinace je v užším kandidátním poolu, ale finální diverzifikace ji nevybrala, "
            f"protože sdílí až {result.closest_selected_overlap} čísel s jinou vybranou kombinací."
        )
    return (
        "Kombinace je v užším kandidátním poolu, ale do finálního diverzifikovaného výběru se nedostala. "
        "Finální výběr upřednostnil jiné kandidáty podle skóre, diverzity a nastavených limitů."
    )


def check_custom_combination(
    raw_value: str,
    *,
    config: AppConfig,
    historical_context: HistoricalContext,
    selected: list[CombinationCandidate],
    candidate_pool: list[CombinationCandidate] | None = None,
    candidate_pool_numbers: Collection[NumberTuple] | None = None,
    candidate_pool_score_cutoff: float | None = None,
) -> CombinationCheckResult:
    """Zkontroluje kombinaci proti filtrům, scoringu, poolu i finálnímu výběru.

    Pro web lze místo plných objektů kandidátního poolu předat kompaktní kolekci
    ``candidate_pool_numbers`` a uloženou hranici skóre. Tím se v session nemusí
    uchovávat celý velký kandidátní pool.
    """
    numbers, input_errors = parse_combination_input(raw_value, config)
    pool_membership_known = candidate_pool is not None or candidate_pool_numbers is not None
    if candidate_pool is not None:
        pool_ranks = _rank_lookup(candidate_pool)
        pool_numbers: Collection[NumberTuple] = pool_ranks
        cutoff = min((candidate.score.total_score for candidate in candidate_pool), default=None)
    else:
        pool_ranks = {}
        pool_numbers = candidate_pool_numbers or ()
        cutoff = candidate_pool_score_cutoff

    if input_errors:
        partial = CombinationCheckResult(
            raw_input=raw_value,
            numbers=numbers,
            input_errors=input_errors,
            candidate_pool_membership_known=pool_membership_known,
        )
        return CombinationCheckResult(
            raw_input=raw_value,
            numbers=numbers,
            input_errors=input_errors,
            candidate_pool_membership_known=pool_membership_known,
            reason=_build_reason(result=partial, config=config, candidate_pool_cutoff=cutoff),
        )

    metrics = calculate_combination_metrics(numbers, config, historical_context, include_historical_overlap=True)
    filter_result = apply_hard_filters(
        numbers,
        metrics,
        historical_context,
        config,
        include_historical_checks=True,
    )
    score = score_combination(metrics, historical_context, config) if filter_result.passed else None
    passes_min_score = bool(score and score.total_score >= config.scoring.min_score_to_keep)

    final_ranks = _rank_lookup(selected)
    in_candidate_pool = pool_membership_known and numbers in pool_numbers
    in_final_selection = numbers in final_ranks

    partial = CombinationCheckResult(
        raw_input=raw_value,
        numbers=numbers,
        input_errors=(),
        metrics=metrics,
        filter_result=filter_result,
        score=score,
        passes_min_score=passes_min_score,
        candidate_pool_membership_known=pool_membership_known,
        in_candidate_pool=in_candidate_pool,
        candidate_pool_rank=(pool_ranks.get(numbers) or None),
        in_final_selection=in_final_selection,
        final_rank=final_ranks.get(numbers),
        closest_selected_overlap=_closest_selected_overlap(numbers, selected),
    )
    return CombinationCheckResult(
        raw_input=partial.raw_input,
        numbers=partial.numbers,
        input_errors=partial.input_errors,
        metrics=partial.metrics,
        filter_result=partial.filter_result,
        score=partial.score,
        passes_min_score=partial.passes_min_score,
        candidate_pool_membership_known=partial.candidate_pool_membership_known,
        in_candidate_pool=partial.in_candidate_pool,
        candidate_pool_rank=partial.candidate_pool_rank,
        in_final_selection=partial.in_final_selection,
        final_rank=partial.final_rank,
        closest_selected_overlap=partial.closest_selected_overlap,
        reason=_build_reason(result=partial, config=config, candidate_pool_cutoff=cutoff),
    )

