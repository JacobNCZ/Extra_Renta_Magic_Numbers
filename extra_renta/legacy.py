"""Kompatibilní veřejná fasáda hlavních funkcí projektu."""

from __future__ import annotations

from .analytics import (
    benchmark_run,
    compare_presets,
    print_historical_validation_report,
    run_quick_test,
    sensitivity_analysis,
)
from .analytics import (
    classification_for_quick_test as _classification_for_quick_test,
)
from .candidate_pool import FULL_MODE, SAMPLE_MODE
from .candidate_pool import build_candidate_pool as _run_pipeline
from .cli import (
    RUN_MODE_DETAILS,
    RunOptions,
    argv_or_sys,
    choose_interactive_run_options,
    choose_preset,
    choose_run_mode,
    format_run_mode_menu,
    maybe_use_last_run_options,
    parse_args,
)
from .pipeline import DEFAULT_DRY_RUN_SAMPLE_SIZE, DEFAULT_SAMPLE_SIZE, PipelineResult, run, run_pipeline
from .presets import DEFAULT_PRESET_KEY, PRESETS, PresetConfig, get_preset
from .selection_pipeline import MMR_SELECTION

__all__ = [
    "DEFAULT_DRY_RUN_SAMPLE_SIZE",
    "DEFAULT_SAMPLE_SIZE",
    "DEFAULT_PRESET_KEY",
    "FULL_MODE",
    "SAMPLE_MODE",
    "MMR_SELECTION",
    "PRESETS",
    "PresetConfig",
    "PipelineResult",
    "RUN_MODE_DETAILS",
    "RunOptions",
    "_classification_for_quick_test",
    "_run_pipeline",
    "argv_or_sys",
    "benchmark_run",
    "choose_interactive_run_options",
    "choose_preset",
    "choose_run_mode",
    "compare_presets",
    "format_run_mode_menu",
    "get_preset",
    "maybe_use_last_run_options",
    "parse_args",
    "print_historical_validation_report",
    "run",
    "run_pipeline",
    "run_quick_test",
    "sensitivity_analysis",
]
