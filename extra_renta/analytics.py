"""Pomocné analytické běhy nad předvolbami Extra Renta."""

from __future__ import annotations

from dataclasses import replace

from .core.models import DiversityConfig, HistoricalContext, RunStats
from .core.statistics import build_historical_context
from .data.historical_draws import HISTORICAL_DRAWS
from .pipeline import SAMPLE_MODE, run_pipeline
from .presets import PRESETS, PresetConfig


def classification_for_quick_test(stats: RunStats, max_output_count: int) -> str:
    """Vrátí praktické vyhodnocení přísnosti nastavení."""
    if stats.generated == 0:
        return "nelze vyhodnotit"
    pass_ratio = stats.passed_min_score / stats.generated
    if stats.passed_hard_filters == 0 or stats.passed_min_score == 0:
        return "příliš přísné - skoro nic neprošlo"
    if stats.final_selected < min(max_output_count, 50) * 0.25:
        return "pravděpodobně velmi přísné ve finálním portfoliu"
    if pass_ratio > 0.35:
        return "spíš volnější - pro kompletní běh může projít hodně kandidátů"
    return "použitelné pro další test nebo kompletní běh"


def run_quick_test(
    preset: PresetConfig,
    historical_context: HistoricalContext,
    *,
    sample_size: int = 20_000,
    seed: int | None = 42,
    check_combination: str | None = None,
) -> RunStats:
    """Spustí rychlý diagnostický vzorek bez exportu."""
    print("=== DIAGNOSTICKÝ DRY-RUN ===")
    print("Výsledky slouží k rychlé kontrole nastavení, ne jako finální výstup.\n")
    result = run_pipeline(
        preset,
        historical_context,
        generation_mode=SAMPLE_MODE,
        sample_size=sample_size,
        seed=seed,
        export_outputs=False,
        phase_label="Rychlý test nastavení",
        check_combination=check_combination,
    )
    print("=== VYHODNOCENÍ RYCHLÉHO TESTU ===")
    print(classification_for_quick_test(result.stats, preset.config.diversity.max_output_count))
    print()
    return result.stats


def compare_presets(*, sample_size: int = 20_000, seed: int | None = 42) -> list[tuple[str, RunStats]]:
    """Porovná všechny předvolby na stejném náhodném vzorku."""
    results: list[tuple[str, RunStats]] = []
    for preset in PRESETS.values():
        context = build_historical_context(HISTORICAL_DRAWS, preset.config)
        result = run_pipeline(
            preset,
            context,
            generation_mode=SAMPLE_MODE,
            sample_size=sample_size,
            seed=seed,
                export_outputs=False,
            phase_label=f"Porovnání předvolby: {preset.label}",
        )
        results.append((preset.label, result.stats))
    return results


def sensitivity_analysis(
    preset: PresetConfig,
    historical_context: HistoricalContext,
    *,
    sample_size: int = 10_000,
    seed: int | None = 42,
) -> list[tuple[str, RunStats]]:
    """Otestuje citlivost tvrdého limitu vzájemného překryvu."""
    base_div = preset.config.diversity
    variants: list[tuple[str, DiversityConfig]] = []
    for overlap in sorted({
        max(0, base_div.max_overlap_between_selected - 1),
        base_div.max_overlap_between_selected,
        base_div.max_overlap_between_selected + 1,
    }):
        variants.append((f"max_overlap={overlap}", replace(base_div, max_overlap_between_selected=overlap)))

    results: list[tuple[str, RunStats]] = []
    for label, div_config in variants:
        cfg = replace(preset.config, diversity=div_config)
        patched = replace(preset, key=f"{preset.key}_{label}", label=f"{preset.label} / {label}", config=cfg)
        result = run_pipeline(
            patched,
            historical_context,
            generation_mode=SAMPLE_MODE,
            sample_size=sample_size,
            seed=seed,
                export_outputs=False,
            phase_label=f"Citlivost: {label}",
        )
        results.append((label, result.stats))
    return results


def print_historical_validation_report(context: HistoricalContext) -> None:
    print("=== VALIDACE HISTORICKÝCH DAT ===")
    for key, value in context.validation_summary().items():
        print(f"{key}: {value}")
    print()


def benchmark_run(
    preset: PresetConfig,
    historical_context: HistoricalContext,
    *,
    sample_size: int = 20_000,
) -> RunStats:
    """Spustí krátký benchmark přes diagnostický vzorek."""
    result = run_pipeline(
        preset,
        historical_context,
        generation_mode=SAMPLE_MODE,
        sample_size=sample_size,
        seed=42,
        export_outputs=False,
        phase_label="Benchmark výkonu",
    )
    return result.stats
