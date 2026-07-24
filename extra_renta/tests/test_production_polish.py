import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from extra_renta.core.models import RunStats
from extra_renta.core.statistics import build_historical_context, normalize_numbers_for_validation
from extra_renta.output.exporter import export_html_report
from extra_renta.presets import get_preset


def test_real_cli_dry_run_subprocess_with_small_sample():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "extra_renta.main",
            "--preset",
            "recommended",
            "--dry-run",
            "--sample-size",
            "50",
            "--seed",
            "42",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "DIAGNOSTICKÝ DRY-RUN" in result.stdout
    assert "ne jako finální výstup" in result.stdout
    assert "Monte Carlo" not in result.stdout


def test_package_data_files_are_present():
    assert Path("extra_renta/output/templates/report.html").exists()
    assert Path("extra_renta/output/static/report.css").exists()


def test_normalize_numbers_for_validation_supports_delimited_string():
    numbers, errors = normalize_numbers_for_validation("1, 2, 3, 4; 5;6,7")

    assert numbers == (1, 2, 3, 4, 5, 6, 7)
    assert errors == ()


def test_duplicate_combinations_are_counted_only_from_valid_rows():
    config = get_preset("recommended").config
    context = build_historical_context(
        [
            {"date": "2024-01-01", "numbers": [1, 2, 3]},
            {"date": "2024-01-02", "numbers": [1, 2, 3]},
            {"date": "2024-01-03", "numbers": [1, 2, 3, 4, 5, 6, 7]},
            {"date": "2024-01-04", "numbers": [1, 2, 3, 4, 5, 6, 7]},
        ],
        config,
    )

    assert len(context.invalid_draws) == 2
    assert context.duplicate_combinations == ((1, 2, 3, 4, 5, 6, 7),)


def test_html_report_shows_danger_state_preset_comparison_and_mmr(tmp_path):
    preset = get_preset("recommended")
    config = preset.config
    context = build_historical_context([], config)
    stats = RunStats(
        total_possible=10,
        generated=10,
        passed_hard_filters=0,
        passed_min_score=0,
        kept_for_diversity=0,
        final_selected=0,
    )
    path = tmp_path / "danger_report.html"

    export_html_report([], stats, context, path, preset_key=preset.key, preset_label=preset.label, config=config)

    report = path.read_text(encoding="utf-8")
    assert "NIC NEPROŠLO" in report
    assert "Použitá předvolba v kontextu ostatních" in report
    assert "preset-row active" in report
    assert "MMR portfolio výběr" in report
    assert "Monte Carlo" not in report


def test_custom_combination_check_parses_common_formats():
    from extra_renta.combination_check import parse_combination_input

    config = get_preset("recommended").config
    numbers, errors = parse_combination_input("[7, 1; 3 5, 9, 11, 13]", config)

    assert numbers == (1, 3, 5, 7, 9, 11, 13)
    assert errors == ()


def test_run_can_check_custom_combination_without_export():
    from extra_renta.main import SAMPLE_MODE, run

    preset = get_preset("recommended")
    config = replace(
        preset.config,
        scoring=replace(preset.config.scoring, max_candidates_for_diversity=200),
        diversity=replace(preset.config.diversity, max_output_count=50),
    )
    patched = replace(preset, config=config)

    result = run(
        patched,
        generation_mode=SAMPLE_MODE,
        sample_size=500,
        seed=42,
        export_outputs=False,
        check_combination="6, 9, 12, 14, 23, 25, 30",
    )

    assert result.combination_check is not None
    assert result.combination_check.numbers == (6, 9, 12, 14, 23, 25, 30)
    assert result.combination_check.is_valid_input
    assert result.combination_check.hard_filters_passed
    assert result.combination_check.passes_min_score


def test_cli_forwards_check_combination_to_run(monkeypatch):
    from extra_renta import main as main_module

    calls = []
    monkeypatch.setattr(main_module, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    main_module.main([
        "--preset",
        "recommended",
        "--mode",
        "sample",
        "--sample-size",
        "100",
        "--no-export",
        "--check-combination",
        "1 2 3 4 5 6 7",
    ])

    assert len(calls) == 1
    _, kwargs = calls[0]
    assert kwargs["check_combination"] == "1 2 3 4 5 6 7"
    assert kwargs["export_outputs"] is False


def test_dry_run_forwards_check_combination_to_quick_test(monkeypatch):
    from extra_renta import main as main_module

    calls = []
    monkeypatch.setattr(
        main_module,
        "run_quick_test",
        lambda preset, context, **kwargs: calls.append((preset, kwargs)),
    )

    main_module.main([
        "--preset",
        "recommended",
        "--dry-run",
        "--sample-size",
        "50",
        "--check-combination",
        "1 2 3 4 5 6 7",
    ])

    assert len(calls) == 1
    _, kwargs = calls[0]
    assert kwargs["check_combination"] == "1 2 3 4 5 6 7"


def test_custom_combination_check_accepts_compact_pool_snapshot():
    from extra_renta.combination_check import check_custom_combination
    from extra_renta.core.statistics import build_historical_context

    preset = get_preset("recommended")
    config = preset.config
    context = build_historical_context([], config)
    numbers = (6, 9, 12, 14, 23, 25, 30)

    check = check_custom_combination(
        "6, 9, 12, 14, 23, 25, 30",
        config=config,
        historical_context=context,
        selected=[],
        candidate_pool=None,
        candidate_pool_numbers=frozenset({numbers}),
        candidate_pool_score_cutoff=0.0,
    )

    assert check.candidate_pool_membership_known
    assert check.in_candidate_pool
