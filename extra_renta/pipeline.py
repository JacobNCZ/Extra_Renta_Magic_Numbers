"""Výpočetní pipeline Extra Renta.

Pipeline provede generování, jednorázový výpočet metrik, filtry, scoring,
tvorbu kandidátního poolu a deterministický MMR portfolio výběr.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from .candidate_pool import FULL_MODE, SAMPLE_MODE, build_candidate_pool
from .combination_check import CombinationCheckResult, check_custom_combination
from .core.combination_generator import total_combination_count
from .core.config_validation import validate_app_config
from .core.models import CombinationCandidate, HistoricalContext, RunStats
from .core.statistics import build_historical_context
from .data.historical_draws import HISTORICAL_DRAWS
from .output.exporter import (
    export_candidates_to_csv,
    export_candidates_to_json,
    export_html_report,
    export_last_run_config,
    export_run_stats_to_json,
)
from .output.printer import (
    evaluate_strictness,
    print_combination_check_result,
    print_disclaimer,
    print_filter_throughput,
    print_final_summary,
    print_historical_summary,
    print_output_limit_info,
    print_run_stats,
    print_strictness_check,
    print_top_candidates,
)
from .presets import PresetConfig
from .selection_pipeline import select_final_candidates

LOGGER = logging.getLogger(__name__)

DEFAULT_SAMPLE_SIZE = 100_000
DEFAULT_DRY_RUN_SAMPLE_SIZE = 20_000
OUTPUT_MODE_CLI = "cli"
OUTPUT_MODE_SILENT = "silent"
ProgressCallback = Callable[[int, int, RunStats], None]
SelectionProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class PipelineResult:
    """Výsledek jedné výpočetní pipeline."""

    selected: list[CombinationCandidate]
    stats: RunStats
    historical_context: HistoricalContext
    preset_key: str
    preset_label: str
    candidate_pool: list[CombinationCandidate] | None = None
    combination_check: CombinationCheckResult | None = None


def _run_options_payload(
    preset: PresetConfig,
    *,
    generation_mode: str,
    sample_size: int,
    seed: int | None,
) -> dict[str, object]:
    return {
        "preset_key": preset.key,
        "preset_label": preset.label,
        "generation_mode": generation_mode,
        "sample_size": sample_size,
        "seed": seed,
        "selection_strategy": "mmr",
        "max_output_count": preset.config.diversity.max_output_count,
    }


def validate_or_raise(preset: PresetConfig) -> None:
    validation = validate_app_config(preset.config)
    for warning in validation.warnings:
        LOGGER.warning("Varování konfigurace: %s", warning)
    validation.raise_for_errors()


def _log_pipeline_start(
    *,
    phase_label: str,
    stats: RunStats,
    generation_mode: str,
    sample_size: int,
    preset: PresetConfig,
) -> None:
    LOGGER.info("Start fáze: %s", phase_label)
    LOGGER.info("Režim generování kombinací: %s", generation_mode)
    LOGGER.info("Celkem možných kombinací: %s", f"{stats.total_possible:,}")
    if generation_mode == SAMPLE_MODE:
        LOGGER.info("Diagnostický vzorek: %s", f"{sample_size:,}")
    LOGGER.info("Zvolená předvolba: %s", preset.label)


def _export_pipeline_result(
    *,
    selected: list[CombinationCandidate],
    stats: RunStats,
    historical_context: HistoricalContext,
    preset: PresetConfig,
    pipeline_start: float,
) -> None:
    config = preset.config
    export_start = time.perf_counter()
    export_candidates_to_csv(selected, config.export.csv_path)
    export_candidates_to_json(selected, config.export.json_path, config=config)
    stats.benchmark.export_seconds = time.perf_counter() - export_start
    stats.benchmark.total_seconds = time.perf_counter() - pipeline_start
    export_html_report(
        selected,
        stats,
        historical_context,
        config.export.html_report_path,
        preset_key=preset.key,
        preset_label=preset.label,
        config=config,
    )
    stats.benchmark.export_seconds = time.perf_counter() - export_start
    stats.benchmark.total_seconds = time.perf_counter() - pipeline_start
    export_run_stats_to_json(
        stats,
        config.export.stats_path,
        preset_key=preset.key,
        preset_label=preset.label,
        config=config,
        historical_context=historical_context,
    )


def _print_pipeline_result(
    *,
    phase_label: str,
    stats: RunStats,
    selected: list[CombinationCandidate],
    max_output_count: int,
) -> None:
    print(f"=== {phase_label.upper()} ===")
    print_run_stats(stats)
    print_filter_throughput(stats)
    print_strictness_check(stats, max_output_count)
    print_output_limit_info(stats, max_output_count)
    print_final_summary(stats, max_output_count)
    print_top_candidates(selected, limit=10, show_score_breakdown=False)


def run_pipeline(
    preset: PresetConfig,
    historical_context: HistoricalContext,
    *,
    generation_mode: str,
    sample_size: int,
    seed: int | None,
    export_outputs: bool,
    phase_label: str,
    check_combination: str | None = None,
    output_mode: str = OUTPUT_MODE_CLI,
    progress_callback: ProgressCallback | None = None,
    selection_progress_callback: SelectionProgressCallback | None = None,
) -> PipelineResult:
    """Spustí jednu pipeline a vrátí strukturovaný výsledek."""
    validate_or_raise(preset)
    config = preset.config
    pipeline_start = time.perf_counter()
    stats = RunStats(
        total_possible=total_combination_count(config.generator),
        invalid_historical_rows=len(historical_context.invalid_draws),
        generation_mode=generation_mode,
        sample_size=sample_size if generation_mode == SAMPLE_MODE else None,
        random_seed=seed if generation_mode == SAMPLE_MODE else None,
    )

    if output_mode == OUTPUT_MODE_CLI:
        _log_pipeline_start(
            phase_label=phase_label,
            stats=stats,
            generation_mode=generation_mode,
            sample_size=sample_size,
            preset=preset,
        )

    pool_result = build_candidate_pool(
        preset,
        historical_context,
        generation_mode=generation_mode,
        sample_size=sample_size,
        seed=seed,
        stats=stats,
        progress_callback=progress_callback,
        log_progress=output_mode == OUTPUT_MODE_CLI,
    )

    selection_result = select_final_candidates(
        pool_result.candidates,
        config,
        progress_callback=selection_progress_callback,
        log_output=output_mode == OUTPUT_MODE_CLI,
    )
    selected = selection_result.selection.selected
    combination_check = (
        check_custom_combination(
            check_combination,
            config=config,
            historical_context=historical_context,
            candidate_pool=pool_result.candidates,
            selected=selected,
        )
        if check_combination
        else None
    )
    stats.diversity_diagnostics = selection_result.selection.diagnostics
    stats.final_selected = len(selected)
    stats.strictness_warnings = evaluate_strictness(stats, config.diversity.max_output_count)
    stats.benchmark.generation_filter_scoring_seconds = pool_result.duration_seconds
    stats.benchmark.selection_seconds = selection_result.duration_seconds
    stats.benchmark.combinations_per_second = (
        stats.generated / pool_result.duration_seconds if pool_result.duration_seconds > 0 else 0.0
    )

    if export_outputs:
        _export_pipeline_result(
            selected=selected,
            stats=stats,
            historical_context=historical_context,
            preset=preset,
            pipeline_start=pipeline_start,
        )
    else:
        stats.benchmark.export_seconds = 0.0
        stats.benchmark.total_seconds = time.perf_counter() - pipeline_start

    if output_mode == OUTPUT_MODE_CLI:
        _print_pipeline_result(
            phase_label=phase_label,
            stats=stats,
            selected=selected,
            max_output_count=config.diversity.max_output_count,
        )
        if combination_check is not None:
            print_combination_check_result(combination_check)
        LOGGER.info("Fáze hotová: %s", phase_label)

    return PipelineResult(
        selected=selected,
        stats=stats,
        historical_context=historical_context,
        preset_key=preset.key,
        preset_label=preset.label,
        candidate_pool=pool_result.candidates,
        combination_check=combination_check,
    )


def run(
    preset: PresetConfig,
    *,
    generation_mode: str = FULL_MODE,
    sample_size: int | None = None,
    seed: int | None = None,
    export_outputs: bool = True,
    check_combination: str | None = None,
    output_mode: str = OUTPUT_MODE_CLI,
    progress_callback: ProgressCallback | None = None,
    selection_progress_callback: SelectionProgressCallback | None = None,
) -> PipelineResult:
    """Spustí kompletní nebo diagnostický vzorkovaný běh s MMR výběrem."""
    if output_mode == OUTPUT_MODE_CLI:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    validate_or_raise(preset)
    resolved_sample_size = sample_size if sample_size is not None else DEFAULT_SAMPLE_SIZE

    if output_mode == OUTPUT_MODE_CLI:
        print_disclaimer()
        print(f"Použité nastavení: {preset.label}")
        print(f"Popis nastavení:   {preset.description}")
        print(f"Režim běhu:        {generation_mode}")
        if generation_mode == SAMPLE_MODE:
            print(f"Velikost vzorku:   {resolved_sample_size:,}".replace(",", " "))
        if not export_outputs:
            print("Export:             vypnutý")
        print()

    historical_context = build_historical_context(HISTORICAL_DRAWS, preset.config)
    if output_mode == OUTPUT_MODE_CLI:
        print_historical_summary(historical_context)

    result = run_pipeline(
        preset,
        historical_context,
        generation_mode=generation_mode,
        sample_size=resolved_sample_size,
        seed=seed,
        export_outputs=export_outputs,
        phase_label="Výsledný běh",
        check_combination=check_combination,
        output_mode=output_mode,
        progress_callback=progress_callback,
        selection_progress_callback=selection_progress_callback,
    )

    if export_outputs:
        export_last_run_config(
            preset.config.export.last_run_config_path,
            _run_options_payload(
                preset,
                generation_mode=generation_mode,
                sample_size=resolved_sample_size,
                seed=seed,
            ),
        )

    if output_mode == OUTPUT_MODE_CLI:
        print("=== POUŽITÉ NASTAVENÍ ===")
        print(f"Klíč:  {preset.key}")
        print(f"Název: {preset.label}")
        print(f"Popis: {preset.description}")
        print("Poznámka: Nastavení pouze omezuje a organizuje kandidátní kombinace.\n")
        LOGGER.info("Hotovo.")
    return result
