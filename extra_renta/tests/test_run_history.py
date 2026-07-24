from __future__ import annotations

from dataclasses import replace

from extra_renta.core.filters import apply_hard_filters
from extra_renta.core.mmr_selector import select_candidates_with_mmr
from extra_renta.core.models import CombinationCandidate, RunStats
from extra_renta.core.scoring import score_combination
from extra_renta.core.statistics import build_historical_context, calculate_combination_metrics
from extra_renta.pipeline import FULL_MODE, PipelineResult
from extra_renta.presets import get_preset
from extra_renta.web_app.run_history import (
    clear_first_place_history,
    delete_first_place_run,
    first_place_history_csv,
    get_first_place_run,
    list_first_place_runs,
    save_first_place_run,
)
from extra_renta.web_app.service import WebRunOptions


def _result():
    preset = get_preset("recommended")
    config = replace(preset.config, diversity=replace(preset.config.diversity, max_output_count=5))
    context = build_historical_context([], config)
    numbers = (4, 9, 13, 18, 22, 27, 31)
    metrics = calculate_combination_metrics(numbers, config, context)
    filter_result = apply_hard_filters(numbers, metrics, context, config)
    score = score_combination(metrics, context, config)
    candidate = CombinationCandidate(numbers, metrics, filter_result, score)
    selected = select_candidates_with_mmr([candidate], config)
    stats = RunStats(
        total_possible=100,
        generated=100,
        passed_hard_filters=20,
        passed_min_score=10,
        kept_for_diversity=1,
        final_selected=1,
        generation_mode=FULL_MODE,
        diversity_diagnostics=selected.diagnostics,
    )
    stats.benchmark.total_seconds = 1.25
    return PipelineResult(
        selected=selected.selected,
        stats=stats,
        historical_context=context,
        preset_key=preset.key,
        preset_label=preset.label,
        candidate_pool=[candidate],
    )


def test_first_place_history_roundtrip(tmp_path):
    db = tmp_path / "history.sqlite3"
    result = _result()
    options = WebRunOptions(preset_key="recommended", max_output_count=5)

    record_id = save_first_place_run(result, options, path=db)

    assert record_id is not None
    rows = list_first_place_runs(path=db)
    assert len(rows) == 1
    assert rows[0]["První kombinace"] == "04 09 13 18 22 27 31"
    assert rows[0]["Vybráno"] == 1

    detail = get_first_place_run(record_id, path=db)
    assert detail is not None
    assert detail["candidate"]["numbers"] == [4, 9, 13, 18, 22, 27, 31]
    assert detail["config"]["max_output_count"] == 5
    assert "První kombinace" in first_place_history_csv(path=db)


def test_first_place_history_delete_and_clear(tmp_path):
    db = tmp_path / "history.sqlite3"
    options = WebRunOptions(preset_key="recommended", max_output_count=5)
    first = save_first_place_run(_result(), options, path=db)
    second = save_first_place_run(_result(), options, path=db)

    assert first and second
    assert delete_first_place_run(first, path=db)
    assert len(list_first_place_runs(path=db)) == 1
    assert clear_first_place_history(path=db) == 1
    assert list_first_place_runs(path=db) == []
