"""Vstupní bod programu Extra Renta.

Příklady:
    python -m extra_renta.main --preset recommended --mode full
    python -m extra_renta.main --preset strict --mode sample --sample-size 20000 --seed 42 --no-export
"""

from __future__ import annotations

import sys

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
from .cli import (
    HISTORY_UPDATE_APPLY,
    HISTORY_UPDATE_BACK,
    HISTORY_UPDATE_CHECK_AVAILABLE,
    HISTORY_UPDATE_CHECK_RULES,
    MAIN_ACTION_EXIT,
    MAIN_ACTION_GENERATE,
    MAIN_ACTION_UPDATE_HISTORY,
    RUN_MODE_DETAILS,
    RunOptions,
    _ask_yes_no,
    argv_or_sys,
    ask_optional_int,
    choose_history_update_action,
    choose_interactive_run_options,
    choose_main_action,
    choose_preset,
    choose_run_mode,
    format_history_update_menu,
    format_main_menu,
    format_run_mode_menu,
    maybe_use_last_run_options,
    parse_args,
)
from .core.statistics import build_historical_context
from .data.historical_draws import HISTORICAL_DRAWS
from .history_update.console import (
    print_history_update_apply_result,
    print_history_update_preview,
    print_new_draw_checks,
)
from .history_update.service import apply_history_update, check_new_draws_against_run, fetch_history_update_preview
from .pipeline import (
    DEFAULT_DRY_RUN_SAMPLE_SIZE,
    DEFAULT_SAMPLE_SIZE,
    OUTPUT_MODE_SILENT,
    PipelineResult,
    run,
    run_pipeline,
)
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
    "argv_or_sys",
    "benchmark_run",
    "choose_interactive_run_options",
    "choose_preset",
    "choose_run_mode",
    "compare_presets",
    "format_run_mode_menu",
    "format_main_menu",
    "choose_main_action",
    "format_history_update_menu",
    "choose_history_update_action",
    "get_preset",
    "main",
    "maybe_use_last_run_options",
    "parse_args",
    "print_historical_validation_report",
    "run",
    "run_interactive_main",
    "run_history_update_menu",
    "run_pipeline",
    "run_quick_test",
    "sensitivity_analysis",
]


def _run_interactive_generator() -> None:
    options = choose_interactive_run_options(allow_last_config=False)
    run(
        options.preset,
        generation_mode=options.generation_mode,
        sample_size=options.sample_size,
        seed=options.seed,
    )


def run_history_update_menu() -> None:
    while True:
        action = choose_history_update_action()
        if action == HISTORY_UPDATE_BACK:
            return

        preview = fetch_history_update_preview()
        print_history_update_preview(preview)
        if action == HISTORY_UPDATE_CHECK_AVAILABLE:
            continue

        if action == HISTORY_UPDATE_CHECK_RULES:
            if preview.source_error or not preview.new_draws:
                continue
            preset = choose_preset()
            sample_size = ask_optional_int(
                "Velikost diagnostického vzorku pro kontrolu nových tahů",
                default=DEFAULT_DRY_RUN_SAMPLE_SIZE,
            )
            result = run(
                preset,
                generation_mode=SAMPLE_MODE,
                sample_size=sample_size,
                seed=42,
                export_outputs=False,
                output_mode=OUTPUT_MODE_SILENT,
            )
            checks = check_new_draws_against_run(
                preview.new_draws,
                config=preset.config,
                historical_context=result.historical_context,
                candidate_pool=result.candidate_pool or [],
                selected=result.selected,
            )
            print_new_draw_checks(checks)
            continue

        if action == HISTORY_UPDATE_APPLY:
            if preview.source_error or not preview.new_draws or preview.conflicting_draws:
                continue
            if not _ask_yes_no("Opravdu uložit nové tahy do lokální historie?", default=False):
                print("Aktualizace zrušena.\n")
                continue
            print_history_update_apply_result(apply_history_update(preview))


def run_interactive_main() -> None:
    while True:
        action = choose_main_action()
        if action == MAIN_ACTION_EXIT:
            print("Konec programu.")
            return
        if action == MAIN_ACTION_GENERATE:
            _run_interactive_generator()
            return
        if action == MAIN_ACTION_UPDATE_HISTORY:
            run_history_update_menu()


def main(argv: list[str] | None = None) -> None:
    raw_argv = argv_or_sys(argv)
    args = parse_args(raw_argv)
    if args.interactive or not raw_argv:
        run_interactive_main()
        return

    preset = get_preset(args.preset)
    if args.dry_run:
        context = build_historical_context(HISTORICAL_DRAWS, preset.config)
        run_quick_test(
            preset,
            context,
            sample_size=args.sample_size or DEFAULT_DRY_RUN_SAMPLE_SIZE,
            seed=args.seed,
            check_combination=args.check_combination,
        )
        return

    run(
        preset,
        generation_mode=args.mode,
        sample_size=args.sample_size,
        seed=args.seed,
        export_outputs=not args.no_export,
        check_combination=args.check_combination,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
