"""Validace aplikační konfigurace před spuštěním výpočtu."""

from __future__ import annotations

from dataclasses import dataclass

from .models import AppConfig


@dataclass(frozen=True)
class ConfigValidationResult:
    """Výsledek validace konfigurace."""

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            formatted = "\n".join(f"- {message}" for message in self.errors)
            raise ValueError(f"Neplatná konfigurace Extra Renta:\n{formatted}")


def _check_range(name: str, range_: tuple[int, int], errors: list[str]) -> None:
    start, end = range_
    if start > end:
        errors.append(f"{name}: začátek rozsahu je větší než konec ({start} > {end})")


def validate_app_config(config: AppConfig) -> ConfigValidationResult:
    """Zkontroluje konzistenci generátoru, filtrů, scoringu a MMR."""
    errors: list[str] = []
    warnings: list[str] = []

    gen = config.generator
    filters = config.filters
    scoring = config.scoring
    diversity = config.diversity
    mmr = config.mmr

    if gen.number_min > gen.number_max:
        errors.append("generator: number_min musí být menší nebo roven number_max")
    available_numbers = gen.number_max - gen.number_min + 1
    if gen.pick_count <= 0:
        errors.append("generator: pick_count musí být kladné číslo")
    if gen.pick_count > available_numbers:
        errors.append("generator: pick_count nesmí být větší než počet dostupných čísel")

    if filters.sum_min > filters.sum_max:
        errors.append("filters: sum_min musí být menší nebo roven sum_max")
    if filters.min_span > filters.max_span:
        errors.append("filters: min_span musí být menší nebo roven max_span")
    if filters.max_single_gap < 0:
        errors.append("filters: max_single_gap nesmí být záporný")
    if filters.min_non_empty_tiers < 0 or filters.min_non_empty_buckets < 0:
        errors.append("filters: minimální počty neprázdných pásem nesmí být záporné")
    if filters.max_historical_overlap > gen.pick_count:
        errors.append("filters: max_historical_overlap nesmí být větší než pick_count")

    _check_range("filters.low_range", filters.low_range, errors)
    for index, range_ in enumerate(filters.tier_ranges, start=1):
        _check_range(f"filters.tier_ranges[{index}]", range_, errors)
    for index, range_ in enumerate(filters.bucket_ranges, start=1):
        _check_range(f"filters.bucket_ranges[{index}]", range_, errors)

    if not filters.allowed_odd_counts:
        errors.append("filters: allowed_odd_counts nesmí být prázdné")
    if any(count < 0 or count > gen.pick_count for count in filters.allowed_odd_counts):
        errors.append("filters: allowed_odd_counts obsahuje hodnotu mimo rozsah 0..pick_count")
    if not filters.allowed_low_counts:
        errors.append("filters: allowed_low_counts nesmí být prázdné")
    if any(count < 0 or count > gen.pick_count for count in filters.allowed_low_counts):
        errors.append("filters: allowed_low_counts obsahuje hodnotu mimo rozsah 0..pick_count")

    if scoring.max_score <= 0:
        errors.append("scoring: max_score musí být kladné číslo")
    if scoring.min_score_to_keep < 0:
        errors.append("scoring: min_score_to_keep nesmí být záporné")
    if scoring.min_score_to_keep > scoring.max_score:
        errors.append("scoring: min_score_to_keep nesmí být větší než max_score")
    if scoring.max_candidates_for_diversity <= 0:
        errors.append("scoring: max_candidates_for_diversity musí být kladné číslo")

    total_weight = sum(float(value) for value in scoring.weights.values())
    if abs(total_weight - scoring.max_score) > 0.001:
        warnings.append(
            f"scoring: součet vah je {total_weight:.3f}, ale max_score je {scoring.max_score:.3f}"
        )
    if any(float(value) < 0 for value in scoring.weights.values()):
        errors.append("scoring: váhy nesmí být záporné")

    if diversity.max_output_count <= 0:
        errors.append("diversity: max_output_count musí být kladné číslo")
    if diversity.max_output_count > scoring.max_candidates_for_diversity:
        warnings.append(
            "diversity: max_output_count je větší než kandidátní pool; skutečný výstup bude omezen velikostí poolu"
        )
    if diversity.max_overlap_between_selected < 0:
        errors.append("diversity: max_overlap_between_selected nesmí být záporný")
    if diversity.max_overlap_between_selected >= gen.pick_count:
        warnings.append("diversity: max_overlap_between_selected je velmi volný; diverzifikace bude slabší")
    if diversity.max_pair_reuse < 1 or diversity.max_triplet_reuse < 1:
        errors.append("diversity: max_pair_reuse a max_triplet_reuse musí být alespoň 1")

    mmr_weights = (
        mmr.score_weight,
        mmr.number_balance_weight,
        mmr.pair_coverage_weight,
        mmr.overlap_diversity_weight,
        mmr.pair_reuse_safety_weight,
    )
    if any(weight < 0 for weight in mmr_weights):
        errors.append("mmr: váhy nesmí být záporné")
    if abs(sum(mmr_weights) - 1.0) > 1e-9:
        errors.append("mmr: součet vah musí být přesně 1.0")
    if not 0.0 <= mmr.min_marginal_gain <= 1.0:
        errors.append("mmr: min_marginal_gain musí být v rozsahu 0.0 až 1.0")
    if not 0.0 <= mmr.diversity_reserve_fraction < 1.0:
        errors.append("mmr: diversity_reserve_fraction musí být v rozsahu 0.0 až méně než 1.0")

    return ConfigValidationResult(errors=tuple(errors), warnings=tuple(warnings))
