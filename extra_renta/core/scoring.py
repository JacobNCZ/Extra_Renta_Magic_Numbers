"""Vysvětlitelný scoring engine.

Skóre vyjadřuje, jak dobře kombinace odpovídá předem definovaným pravidlům
vyváženého filtru. Skóre není predikce výhry.
"""

from __future__ import annotations

from .models import AppConfig, CombinationMetrics, HistoricalContext, ScoreBreakdown


def _center_score(value: float, minimum: float, maximum: float, ideal: float, weight: float) -> float:
    """Boduje hodnotu podle vzdálenosti od ideálního středu."""
    if value < minimum or value > maximum:
        return 0.0
    max_distance = max(abs(ideal - minimum), abs(maximum - ideal))
    if max_distance == 0:
        return weight
    distance = abs(value - ideal)
    return max(0.0, weight * (1.0 - distance / max_distance))


def _interval_score(value: float, minimum: float, maximum: float, ideal_min: float, ideal_max: float, weight: float) -> float:
    """Plný počet bodů za ideální interval, částečné body za hraniční interval."""
    if value < minimum or value > maximum:
        return 0.0
    if ideal_min <= value <= ideal_max:
        return weight
    if value < ideal_min:
        denominator = ideal_min - minimum
        return weight if denominator == 0 else weight * ((value - minimum) / denominator)
    denominator = maximum - ideal_max
    return weight if denominator == 0 else weight * ((maximum - value) / denominator)


def score_combination(
    metrics: CombinationMetrics,
    historical_context: HistoricalContext,
    config: AppConfig,
) -> ScoreBreakdown:
    """Spočítá vysvětlitelné skóre 0–100 pro jednu kombinaci."""
    scoring = config.scoring
    weights = scoring.weights

    def weight(key: str, legacy_key: str | None = None) -> float:
        """Vrátí váhu scoringové komponenty včetně kompatibility se starším názvem."""
        if key in weights:
            return float(weights[key])
        if legacy_key and legacy_key in weights:
            return float(weights[legacy_key])
        raise KeyError(f"Chybí scoringová váha: {key}")
    filters = config.filters
    components: dict[str, float] = {}
    notes: list[str] = [
        "Skóre hodnotí vyváženost podle pravidel, ne pravděpodobnost výhry."
    ]

    # 1) Součet: ideál je řízený zvolenou předvolbou.
    components["sum_balance"] = _center_score(
        metrics.total_sum,
        filters.sum_min,
        filters.sum_max,
        ideal=scoring.ideal_sum,
        weight=weight("sum_balance"),
    )

    # 2) Sudá/lichá: preferované počty jsou řízené zvolenou předvolbou.
    if metrics.odd_count in scoring.preferred_odd_counts:
        components["odd_even_balance"] = weight("odd_even_balance")
    elif metrics.odd_count in filters.allowed_odd_counts:
        components["odd_even_balance"] = weight("odd_even_balance") * 0.5
    else:
        components["odd_even_balance"] = 0.0

    # 3) Nízká/vysoká: preferované počty jsou řízené zvolenou předvolbou.
    if metrics.low_count in scoring.preferred_low_counts:
        components["low_high_balance"] = weight("low_high_balance")
    elif metrics.low_count in filters.allowed_low_counts:
        components["low_high_balance"] = weight("low_high_balance") * 0.5
    else:
        components["low_high_balance"] = 0.0

    # 4) Nízká/střední/vysoká pásma: preferovaný počet pásem je v konfiguraci.
    if metrics.non_empty_tiers >= scoring.preferred_min_non_empty_tiers:
        components["tier_balance"] = weight("tier_balance")
    elif metrics.non_empty_tiers >= filters.min_non_empty_tiers:
        components["tier_balance"] = weight("tier_balance") * 0.65
    else:
        components["tier_balance"] = 0.0

    # 5) Jemnější pásma: preferujeme rozprostření bez koncentrace v jednom pásmu.
    if metrics.non_empty_buckets >= scoring.preferred_min_non_empty_buckets and metrics.max_bucket_count <= scoring.preferred_max_bucket_count:
        components["bucket_balance"] = weight("bucket_balance")
    elif metrics.non_empty_buckets >= filters.min_non_empty_buckets and metrics.max_bucket_count <= filters.max_numbers_in_one_bucket:
        components["bucket_balance"] = weight("bucket_balance") * 0.65
    else:
        components["bucket_balance"] = 0.0

    # 6) Rozpětí: ideálně ne moc úzké ani zbytečně krajní.
    components["span_balance"] = _interval_score(
        metrics.span,
        minimum=filters.min_span,
        maximum=filters.max_span,
        ideal_min=scoring.ideal_span_min,
        ideal_max=scoring.ideal_span_max,
        weight=weight("span_balance"),
    )

    # 7) Mezery: kontrola maximální mezery a směrodatné odchylky mezer.
    gap_part = 0.0
    if metrics.max_gap <= scoring.max_gap_for_full_score:
        gap_part += weight("gap_balance") * 0.5
    elif metrics.max_gap <= filters.max_single_gap:
        gap_part += weight("gap_balance") * 0.25

    # Příliš pravidelné i příliš divoké mezery jsou penalizovány jako vzor/extrém.
    gap_part += _interval_score(
        metrics.gap_std,
        minimum=scoring.gap_std_min,
        maximum=scoring.gap_std_max,
        ideal_min=scoring.gap_std_ideal_min,
        ideal_max=scoring.gap_std_ideal_max,
        weight=weight("gap_balance") * 0.5,
    )
    components["gap_balance"] = min(weight("gap_balance"), gap_part)

    # 8) Historická podobnost: slabé analytické kritérium, ne predikce.
    if not historical_context.valid_draws or metrics.max_historical_overlap <= 3:
        components["historical_similarity"] = weight("historical_similarity")
    elif metrics.max_historical_overlap == 4:
        components["historical_similarity"] = weight("historical_similarity") * 0.6
    elif metrics.max_historical_overlap == 5:
        components["historical_similarity"] = weight("historical_similarity") * 0.25
    else:
        components["historical_similarity"] = 0.0

    # 9) Lidské vzory: dlouhé řady, mnoho sousedních dvojic a koncovky.
    pattern_safety_score = weight("pattern_safety", "human_pattern_penalty")
    if metrics.adjacent_pairs > scoring.adjacent_pairs_soft_limit:
        pattern_safety_score *= 0.7
    if metrics.max_consecutive_run_length >= scoring.consecutive_run_soft_limit:
        pattern_safety_score *= 0.75
    if metrics.max_same_last_digit >= scoring.same_last_digit_soft_limit:
        pattern_safety_score *= 0.75
    if metrics.gap_std < scoring.gap_std_pattern_min:
        pattern_safety_score *= 0.5
    components["pattern_safety"] = pattern_safety_score

    # 10) Celková rovnoměrnost rozložení: doplňkový souhrnný bonus.
    uniformity = 0.0
    if metrics.non_empty_buckets >= filters.min_non_empty_buckets:
        uniformity += weight("overall_uniformity") * 0.4
    if metrics.adjacent_pairs <= scoring.adjacent_pairs_soft_limit:
        uniformity += weight("overall_uniformity") * 0.3
    if (
        metrics.repeated_from_last_draw <= scoring.repeated_from_last_draw_limit
        and metrics.neighbors_of_last_draw <= scoring.neighbors_of_last_draw_limit
    ):
        uniformity += weight("overall_uniformity") * 0.3
    components["overall_uniformity"] = min(weight("overall_uniformity"), uniformity)

    total = round(min(sum(components.values()), config.scoring.max_score), 4)
    rounded_components = {key: round(value, 4) for key, value in components.items()}

    return ScoreBreakdown(
        total_score=total,
        components=rounded_components,
        notes=tuple(notes),
    )
