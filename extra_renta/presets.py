"""Centrální předvolby konfigurace pro Extra Rentu.

Předvolby upravují pouze praktické filtrování, scoring a složení výstupního
portfolia. Žádná předvolba ani historická data nezvyšují matematickou
pravděpodobnost výhry.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from .core.models import (
    AppConfig,
    DiversityConfig,
    ExportConfig,
    GeneratorConfig,
    HardFilterConfig,
    MMRConfig,
    ScoringConfig,
)

DEFAULT_PRESET_KEY = "recommended"


@dataclass(frozen=True)
class PresetConfig:
    """Jedna uživatelská předvolba včetně reálné aplikační konfigurace."""

    key: str
    label: str
    description: str
    config: AppConfig
    rule_summary: tuple[str, ...]


def _common_generator(mode: str) -> GeneratorConfig:
    return GeneratorConfig(number_min=1, number_max=33, pick_count=7, mode=mode)


def _common_export(suffix: str) -> ExportConfig:
    return ExportConfig(
        csv_path=f"output/final_candidates_{suffix}.csv",
        json_path=f"output/final_candidates_{suffix}.json",
        stats_path=f"output/run_stats_{suffix}.json",
        html_report_path=f"output/report_{suffix}.html",
        last_run_config_path="output/last_run_config.json",
    )


def _make_app_config(
    *,
    mode: str,
    filters: HardFilterConfig,
    scoring: ScoringConfig,
    diversity: DiversityConfig,
    mmr: MMRConfig,
    export_suffix: str,
) -> AppConfig:
    return AppConfig(
        generator=_common_generator(mode=mode),
        filters=filters,
        scoring=scoring,
        diversity=diversity,
        mmr=mmr,
        export=_common_export(export_suffix),
    )


def _weights(
    *,
    sum_balance: float = 15.0,
    odd_even_balance: float = 10.0,
    low_high_balance: float = 10.0,
    tier_balance: float = 10.0,
    bucket_balance: float = 10.0,
    span_balance: float = 10.0,
    gap_balance: float = 10.0,
    historical_similarity: float = 10.0,
    pattern_safety: float = 10.0,
    overall_uniformity: float = 5.0,
) -> Mapping[str, float]:
    return {
        "sum_balance": sum_balance,
        "odd_even_balance": odd_even_balance,
        "low_high_balance": low_high_balance,
        "tier_balance": tier_balance,
        "bucket_balance": bucket_balance,
        "span_balance": span_balance,
        "gap_balance": gap_balance,
        "historical_similarity": historical_similarity,
        "pattern_safety": pattern_safety,
        "overall_uniformity": overall_uniformity,
    }


RECOMMENDED_CONFIG = _make_app_config(
    mode="recommended",
    filters=HardFilterConfig(
        sum_min=105,
        sum_max=150,
        allowed_odd_counts=(2, 3, 4, 5),
        low_range=(1, 17),
        allowed_low_counts=(2, 3, 4, 5),
        tier_ranges=((1, 11), (12, 22), (23, 33)),
        min_non_empty_tiers=2,
        max_numbers_in_one_tier=5,
        bucket_ranges=((1, 9), (10, 19), (20, 29), (30, 33)),
        min_non_empty_buckets=3,
        max_numbers_in_one_bucket=4,
        min_span=18,
        max_span=31,
        max_single_gap=18,
        max_adjacent_pairs=3,
        max_consecutive_run_length=3,
        max_same_last_digit=3,
        exclude_exact_historical_draws=True,
        max_historical_overlap=5,
    ),
    scoring=ScoringConfig(
        weights=_weights(),
        min_score_to_keep=60.0,
        max_score=100.0,
        max_candidates_for_diversity=100_000,
        ideal_sum=119.0,
        preferred_odd_counts=(3, 4),
        preferred_low_counts=(3, 4),
        preferred_min_non_empty_tiers=3,
        preferred_min_non_empty_buckets=4,
        preferred_max_bucket_count=3,
        ideal_span_min=22,
        ideal_span_max=29,
        max_gap_for_full_score=15,
        gap_std_min=1.4,
        gap_std_max=5.0,
        gap_std_ideal_min=1.7,
        gap_std_ideal_max=4.5,
        adjacent_pairs_soft_limit=2,
        consecutive_run_soft_limit=3,
        same_last_digit_soft_limit=3,
        gap_std_pattern_min=1.4,
        repeated_from_last_draw_limit=3,
        neighbors_of_last_draw_limit=4,
    ),
    diversity=DiversityConfig(
        max_output_count=1_000,
        max_overlap_between_selected=4,
        max_pair_reuse=20,
        max_triplet_reuse=5,
        enforce_pair_triplet_limits=False,
    ),
    mmr=MMRConfig(
        score_weight=0.45,
        number_balance_weight=0.20,
        pair_coverage_weight=0.20,
        overlap_diversity_weight=0.10,
        pair_reuse_safety_weight=0.05,
        min_marginal_gain=0.0,
        diversity_reserve_fraction=0.20,
    ),
    export_suffix="recommended",
)


STRICT_CONFIG = _make_app_config(
    mode="strict",
    filters=HardFilterConfig(
        sum_min=115,
        sum_max=140,
        allowed_odd_counts=(3, 4),
        low_range=(1, 17),
        allowed_low_counts=(3, 4),
        tier_ranges=((1, 11), (12, 22), (23, 33)),
        min_non_empty_tiers=3,
        max_numbers_in_one_tier=4,
        bucket_ranges=((1, 9), (10, 19), (20, 29), (30, 33)),
        min_non_empty_buckets=4,
        max_numbers_in_one_bucket=3,
        min_span=20,
        max_span=30,
        max_single_gap=14,
        max_adjacent_pairs=2,
        max_consecutive_run_length=2,
        max_same_last_digit=2,
        exclude_exact_historical_draws=True,
        max_historical_overlap=4,
    ),
    scoring=ScoringConfig(
        weights=_weights(
            sum_balance=15.0,
            odd_even_balance=11.0,
            low_high_balance=11.0,
            tier_balance=11.0,
            bucket_balance=11.0,
            span_balance=10.0,
            gap_balance=10.0,
            historical_similarity=5.0,
            pattern_safety=12.0,
            overall_uniformity=4.0,
        ),
        min_score_to_keep=75.0,
        max_score=100.0,
        max_candidates_for_diversity=75_000,
        ideal_sum=119.0,
        preferred_odd_counts=(3, 4),
        preferred_low_counts=(3, 4),
        preferred_min_non_empty_tiers=3,
        preferred_min_non_empty_buckets=4,
        preferred_max_bucket_count=3,
        ideal_span_min=23,
        ideal_span_max=28,
        max_gap_for_full_score=11,
        gap_std_min=1.6,
        gap_std_max=4.4,
        gap_std_ideal_min=2.0,
        gap_std_ideal_max=4.0,
        adjacent_pairs_soft_limit=1,
        consecutive_run_soft_limit=2,
        same_last_digit_soft_limit=2,
        gap_std_pattern_min=1.6,
        repeated_from_last_draw_limit=2,
        neighbors_of_last_draw_limit=3,
    ),
    diversity=DiversityConfig(
        max_output_count=1_000,
        max_overlap_between_selected=4,
        max_pair_reuse=15,
        max_triplet_reuse=4,
        enforce_pair_triplet_limits=False,
    ),
    mmr=MMRConfig(
        score_weight=0.50,
        number_balance_weight=0.18,
        pair_coverage_weight=0.17,
        overlap_diversity_weight=0.10,
        pair_reuse_safety_weight=0.05,
        min_marginal_gain=0.0,
        diversity_reserve_fraction=0.25,
    ),
    export_suffix="strict",
)


EXPERIMENTAL_STRICT_CONFIG = replace(
    STRICT_CONFIG,
    generator=_common_generator(mode="experimental_strict"),
    diversity=DiversityConfig(
        max_output_count=1_000,
        max_overlap_between_selected=3,
        max_pair_reuse=10,
        max_triplet_reuse=3,
        enforce_pair_triplet_limits=False,
    ),
    mmr=MMRConfig(
        score_weight=0.40,
        number_balance_weight=0.20,
        pair_coverage_weight=0.20,
        overlap_diversity_weight=0.15,
        pair_reuse_safety_weight=0.05,
        min_marginal_gain=0.0,
        diversity_reserve_fraction=0.30,
    ),
    export=_common_export("experimental_strict"),
)


PRESETS: dict[str, PresetConfig] = {
    "recommended": PresetConfig(
        key="recommended",
        label="Doporučené nastavení",
        description="Vyvážené nastavení s mírnějšími filtry a vyváženým MMR výběrem.",
        config=RECOMMENDED_CONFIG,
        rule_summary=(
            "Běžnější rozsah součtu kombinace.",
            "Vyvážený poměr sudých a lichých čísel.",
            "Mírné omezení shluků a jednoduchých vzorů.",
            "MMR vyvažuje individuální skóre, četnosti čísel a pokrytí párů.",
        ),
    ),
    "strict": PresetConfig(
        key="strict",
        label="Přísnější nastavení",
        description="Užší filtry, přísnější strukturální pravidla a vyšší minimální skóre.",
        config=STRICT_CONFIG,
        rule_summary=(
            "Užší rozsah součtu a přísnější poměry.",
            "Silnější omezení shluků, mezer a jednoduchých vzorů.",
            "Vyšší minimální skóre kombinace.",
            "MMR stále používá měkké portfolio preference místo nedosažitelných limitů párů.",
        ),
    ),
    "experimental_strict": PresetConfig(
        key="experimental_strict",
        label="Experimentální velmi přísné nastavení",
        description="Nejpřísnější varianta s maximálním překryvem pouze tří čísel mezi vybranými kombinacemi.",
        config=EXPERIMENTAL_STRICT_CONFIG,
        rule_summary=(
            "Stejné tvrdé filtry a scoring jako přísnější nastavení.",
            "Ještě tvrdší limit vzájemného překryvu.",
            "Vyšší váha portfolio diverzity v MMR.",
            "Skutečný počet může být nižší než maximální limit výstupu.",
        ),
    ),
}


def get_preset(key: str) -> PresetConfig:
    try:
        return PRESETS[key]
    except KeyError as exc:
        available = ", ".join(PRESETS)
        raise ValueError(f"Neznámá předvolba '{key}'. Dostupné předvolby: {available}") from exc


def _format_count_pairs(odd_counts: tuple[int, ...], pick_count: int) -> str:
    return ", ".join(f"{pick_count - odd} sudá / {odd} lichá" for odd in odd_counts)


def _rule_value(preset: PresetConfig, rule_key: str) -> str:
    cfg = preset.config
    filters = cfg.filters
    scoring = cfg.scoring
    diversity = cfg.diversity
    if rule_key == "strictness":
        return {"recommended": "střední", "strict": "vyšší", "experimental_strict": "velmi vysoká"}.get(preset.key, "-")
    if rule_key == "sum_range":
        return f"{filters.sum_min}-{filters.sum_max}"
    if rule_key == "odd_even":
        return _format_count_pairs(filters.allowed_odd_counts, cfg.generator.pick_count)
    if rule_key == "low_count":
        return str(filters.allowed_low_counts)
    if rule_key == "span":
        return f"{filters.min_span}-{filters.max_span}"
    if rule_key == "adjacent":
        return f"max {filters.max_adjacent_pairs} dvojice"
    if rule_key == "historical_overlap":
        return f"max {filters.max_historical_overlap} čísel"
    if rule_key == "min_score":
        return f"{scoring.min_score_to_keep:g} bodů"
    if rule_key == "diversity_overlap":
        return f"max {diversity.max_overlap_between_selected} čísla"
    if rule_key == "pair_triplet":
        return "měkké MMR preference" if not diversity.enforce_pair_triplet_limits else f"pár {diversity.max_pair_reuse}x, trojice {diversity.max_triplet_reuse}x"
    if rule_key == "selection":
        return "deterministické MMR"
    if rule_key == "max_output":
        return f"max {diversity.max_output_count:,}".replace(",", " ")
    return "-"


def preset_comparison_rows() -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for preset in PRESETS.values():
        rows.append({
            "key": preset.key,
            "label": preset.label,
            "strictness": _rule_value(preset, "strictness"),
            "sum_range": _rule_value(preset, "sum_range"),
            "min_score": _rule_value(preset, "min_score"),
            "diversity_overlap": _rule_value(preset, "diversity_overlap"),
            "pair_triplet": _rule_value(preset, "pair_triplet"),
            "selection": _rule_value(preset, "selection"),
            "max_output": _rule_value(preset, "max_output"),
        })
    return tuple(rows)


def _table_line(widths: tuple[int, ...], *, left: str = "+", fill: str = "-") -> str:
    return left + left.join(fill * (width + 2) for width in widths) + left


def _table_row(values: tuple[str, ...], widths: tuple[int, ...]) -> str:
    return "|" + "|".join(f" {value:<{width}} " for value, width in zip(values, widths, strict=True)) + "|"


def format_preset_comparison_table() -> str:
    presets = tuple(PRESETS.values())
    rows: tuple[tuple[str, str], ...] = (
        ("Přísnost", "strictness"),
        ("Součet čísel", "sum_range"),
        ("Sudá / lichá", "odd_even"),
        ("Nízká čísla", "low_count"),
        ("Rozpětí", "span"),
        ("Sousední dvojice", "adjacent"),
        ("Historický překryv", "historical_overlap"),
        ("Minimální skóre", "min_score"),
        ("Překryv finálních", "diversity_overlap"),
        ("Páry / trojice", "pair_triplet"),
        ("Finální výběr", "selection"),
        ("Limit výstupu", "max_output"),
    )
    headers = ("Pravidlo", "Doporučené", "Přísnější", "Experimentální")
    table_rows = [headers]
    for label, key in rows:
        table_rows.append((label, *(_rule_value(preset, key) for preset in presets)))
    widths = tuple(max(len(row[index]) for row in table_rows) for index in range(len(headers)))
    lines = ["=== POROVNÁNÍ PŘEDVOLEB ===", _table_line(widths), _table_row(headers, widths), _table_line(widths)]
    lines.extend(_table_row(row, widths) for row in table_rows[1:])
    lines.append(_table_line(widths))
    lines.append("MMR se spouští až po filtrech a scoringu nad kandidátním poolem.")
    return "\n".join(lines)


def format_preset_menu() -> str:
    lines = [
        "=== VÝBĚR PŘEDVOLBY NASTAVENÍ ===",
        "Všechny předvolby používají stejnou pipeline: filtry → scoring → MMR portfolio výběr → report.",
        "",
    ]
    for index, preset in enumerate(PRESETS.values(), start=1):
        lines.extend((f"{index}. {preset.label}", f"   {preset.description}"))
    lines.extend(("", format_preset_comparison_table(), "", "Žádná předvolba ani historická data nezvyšují matematickou pravděpodobnost výhry."))
    return "\n".join(lines)


def format_preset_detail(preset: PresetConfig) -> str:
    cfg = preset.config
    filters = cfg.filters
    scoring = cfg.scoring
    diversity = cfg.diversity
    mmr = cfg.mmr
    lines = [
        f"=== DETAIL PŘEDVOLBY: {preset.label} ===",
        preset.description,
        "",
        "Co tato předvolba ovlivní:",
        *(f"- {item}" for item in preset.rule_summary),
        "",
        "Tvrdé filtry:",
        f"- Součet kombinace: {filters.sum_min} až {filters.sum_max}",
        f"- Povolený poměr sudá/lichá: {_format_count_pairs(filters.allowed_odd_counts, cfg.generator.pick_count)}",
        f"- Rozpětí kombinace: {filters.min_span} až {filters.max_span}",
        f"- Maximální historický překryv: {filters.max_historical_overlap}",
        "",
        "Scoring:",
        f"- Minimální skóre: {scoring.min_score_to_keep}",
        f"- Limit kandidátního poolu: {scoring.max_candidates_for_diversity:,}".replace(",", " "),
        "",
        "Finální portfolio:",
        f"- Maximální limit výstupu: {diversity.max_output_count:,}".replace(",", " "),
        f"- Maximální překryv mezi vybranými kandidáty: {diversity.max_overlap_between_selected}",
        "- Menší počet než limit je platný výsledek.",
        "- Páry a trojice jsou standardně měkkou MMR preferencí, nikoli nedosažitelným cílem.",
        "",
        "MMR váhy:",
        f"- Individuální skóre: {mmr.score_weight:.2f}",
        f"- Vyváženost čísel: {mmr.number_balance_weight:.2f}",
        f"- Pokrytí párů: {mmr.pair_coverage_weight:.2f}",
        f"- Diverzita překryvu: {mmr.overlap_diversity_weight:.2f}",
        f"- Bezpečnost opakování párů: {mmr.pair_reuse_safety_weight:.2f}",
    ]
    return "\n".join(lines)
