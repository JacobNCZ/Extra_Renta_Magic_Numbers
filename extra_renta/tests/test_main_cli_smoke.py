import json
from dataclasses import replace
from pathlib import Path

from extra_renta.main import FULL_MODE, SAMPLE_MODE, run
from extra_renta.presets import get_preset


def _tiny_preset(tmp_path=None):
    preset = get_preset("recommended")
    cfg = preset.config
    cfg = replace(
        cfg,
        generator=replace(cfg.generator, number_min=1, number_max=12, pick_count=7, mode="test"),
        filters=replace(
            cfg.filters,
            sum_min=28,
            sum_max=63,
            allowed_odd_counts=tuple(range(8)),
            low_range=(1, 6),
            allowed_low_counts=tuple(range(8)),
            tier_ranges=((1, 4), (5, 8), (9, 12)),
            min_non_empty_tiers=1,
            max_numbers_in_one_tier=7,
            bucket_ranges=((1, 3), (4, 6), (7, 9), (10, 12)),
            min_non_empty_buckets=1,
            max_numbers_in_one_bucket=7,
            min_span=0,
            max_span=11,
            max_single_gap=11,
            max_adjacent_pairs=6,
            max_consecutive_run_length=7,
            max_same_last_digit=7,
            exclude_exact_historical_draws=False,
            max_historical_overlap=7,
        ),
        scoring=replace(
            cfg.scoring,
            min_score_to_keep=0,
            max_candidates_for_diversity=200,
            ideal_sum=45,
            preferred_min_non_empty_tiers=1,
            preferred_min_non_empty_buckets=1,
            ideal_span_min=0,
            ideal_span_max=11,
        ),
        diversity=replace(
            cfg.diversity,
            max_output_count=20,
            max_overlap_between_selected=5,
            enforce_pair_triplet_limits=False,
        ),
    )
    if tmp_path is not None:
        cfg = replace(
            cfg,
            export=replace(
                cfg.export,
                csv_path=str(tmp_path / "candidates.csv"),
                json_path=str(tmp_path / "candidates.json"),
                stats_path=str(tmp_path / "stats.json"),
                html_report_path=str(tmp_path / "report.html"),
                last_run_config_path=str(tmp_path / "last_run_config.json"),
            ),
        )
    return replace(preset, config=cfg)


def test_short_sample_run_exports_mmr_diagnostics(tmp_path):
    preset = _tiny_preset(tmp_path)

    result = run(
        preset,
        generation_mode=SAMPLE_MODE,
        sample_size=100,
        seed=42,
    )

    assert Path(preset.config.export.csv_path).exists()
    payload = json.loads(Path(preset.config.export.stats_path).read_text(encoding="utf-8"))
    assert payload["stats"]["generation_mode"] == SAMPLE_MODE
    assert payload["stats"]["sample_size"] == 100
    assert payload["stats"]["diversity_diagnostics"]["selection_strategy"] == "mmr"
    assert len(result.selected) <= preset.config.diversity.max_output_count


def test_short_full_run_uses_maximum_output_semantics(tmp_path):
    preset = _tiny_preset(tmp_path)

    result = run(preset, generation_mode=FULL_MODE, export_outputs=False)

    assert result.stats.generated == 792
    assert result.stats.final_selected <= preset.config.diversity.max_output_count
    assert result.stats.diversity_diagnostics.max_output_count == 20
    assert result.stats.diversity_diagnostics.stop_reason != "not_started"


def test_interactive_options_collect_preset_and_mode_without_debug(monkeypatch):
    from extra_renta.main import choose_interactive_run_options

    answers = iter(["2", "a", "1"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    options = choose_interactive_run_options(allow_last_config=False)

    assert options.preset.key == "strict"
    assert options.generation_mode == FULL_MODE
    assert not hasattr(options, "debug")


def test_parse_args_accepts_only_full_or_sample():
    from extra_renta.cli import parse_args

    args = parse_args(["--preset", "strict", "--mode", "sample", "--sample-size", "123", "--seed", "7"])

    assert args.preset == "strict"
    assert args.mode == SAMPLE_MODE
    assert args.sample_size == 123
    assert args.seed == 7


def test_cli_forwards_sample_run_to_pipeline(monkeypatch):
    from extra_renta import main as main_module

    calls = []
    monkeypatch.setattr(main_module, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    main_module.main([
        "--preset", "recommended",
        "--mode", "sample",
        "--sample-size", "100",
        "--seed", "9",
        "--no-export",
        "--check-combination", "1 2 3 4 5 6 7",
    ])

    assert len(calls) == 1
    _, kwargs = calls[0]
    assert kwargs["generation_mode"] == SAMPLE_MODE
    assert kwargs["sample_size"] == 100
    assert kwargs["seed"] == 9
    assert kwargs["export_outputs"] is False
    assert kwargs["check_combination"] == "1 2 3 4 5 6 7"


def test_removed_monte_carlo_cli_mode_is_rejected():
    import pytest

    from extra_renta.cli import parse_args

    with pytest.raises(SystemExit):
        parse_args(["--mode", "monte-carlo"])
