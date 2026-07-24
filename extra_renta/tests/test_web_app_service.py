from dataclasses import replace

import pytest

from extra_renta.core.filters import apply_hard_filters
from extra_renta.core.mmr_selector import select_candidates_with_mmr
from extra_renta.core.models import CombinationCandidate, RunStats
from extra_renta.core.scoring import score_combination
from extra_renta.core.statistics import build_historical_context, calculate_combination_metrics
from extra_renta.pipeline import FULL_MODE, PipelineResult
from extra_renta.presets import get_preset
from extra_renta.web_app.service import (
    WEB_MAX_OUTPUT_COUNT,
    WebRunOptions,
    build_export_bundle,
    candidate_selection_reason,
    candidate_to_technical_table_row,
    normalize_web_options,
    options_signature,
    preset_comparison_table_rows,
    preset_detail_rows,
    result_summary,
    run_recommendation,
    run_web_generation,
    validate_web_options,
    web_config_payload,
)


def _candidate(numbers, config):
    context = build_historical_context([], config)
    metrics = calculate_combination_metrics(numbers, config, context)
    filter_result = apply_hard_filters(numbers, metrics, context, config)
    score = score_combination(metrics, context, config)
    return CombinationCandidate(numbers, metrics, filter_result, score)


def _result(max_output_count=5):
    preset = get_preset("recommended")
    config = replace(preset.config, diversity=replace(preset.config.diversity, max_output_count=max_output_count))
    candidate = _candidate((4, 9, 13, 18, 22, 27, 31), config)
    selected_result = select_candidates_with_mmr([candidate], config)
    context = build_historical_context([], config)
    stats = RunStats(
        total_possible=100,
        generated=100,
        passed_hard_filters=20,
        passed_min_score=10,
        kept_for_diversity=1,
        final_selected=1,
        generation_mode=FULL_MODE,
        diversity_diagnostics=selected_result.diagnostics,
    )
    return PipelineResult(
        selected=selected_result.selected,
        stats=stats,
        historical_context=context,
        preset_key=preset.key,
        preset_label=preset.label,
        candidate_pool=[candidate],
    )


def test_web_options_default_to_preset_maximum():
    normalized = normalize_web_options(WebRunOptions(preset_key="strict"))

    assert normalized.max_output_count == get_preset("strict").config.diversity.max_output_count


def test_web_options_validate_maximum_limit():
    validate_web_options(WebRunOptions(preset_key="recommended", max_output_count=1))
    validate_web_options(WebRunOptions(preset_key="recommended", max_output_count=WEB_MAX_OUTPUT_COUNT))

    with pytest.raises(ValueError):
        validate_web_options(WebRunOptions(preset_key="recommended", max_output_count=WEB_MAX_OUTPUT_COUNT + 1))


def test_web_wrapper_forces_full_run_and_mmr(monkeypatch):
    calls = {}

    def fake_run(preset, **kwargs):
        calls["preset"] = preset
        calls.update(kwargs)
        return _result(max_output_count=preset.config.diversity.max_output_count)

    monkeypatch.setattr("extra_renta.web_app.service.run", fake_run)
    run_web_generation(WebRunOptions(preset_key="recommended", max_output_count=22))

    assert calls["generation_mode"] == FULL_MODE
    assert calls["preset"].config.diversity.max_output_count == 22
    assert "sample_size" not in calls
    assert "seed" not in calls


def test_result_summary_and_recommendation_use_maximum_semantics():
    result = _result(max_output_count=5)
    summary = result_summary(result)
    status, recommendation = run_recommendation(result)

    assert summary["Maximální limit výstupu"] == 5
    assert summary["Finálně vybráno"] == 1
    assert summary["Důvod ukončení"] in {"candidate_pool_exhausted", "no_feasible_candidate"}
    assert status == "success"
    assert "platný výsledek" in recommendation


def test_candidate_reason_contains_mmr_contribution():
    candidate = _result().selected[0]

    reason = candidate_selection_reason(candidate)
    row = candidate_to_technical_table_row(candidate, 1)

    assert "MMR marginální přínos" in reason
    assert "MMR přínos" in row
    assert "Nové páry" in row


def test_web_config_and_signature_have_no_monte_carlo_fields():
    options = WebRunOptions(preset_key="recommended", max_output_count=7)
    payload = web_config_payload(options)
    signature = options_signature(options)

    assert payload["selection_strategy"] == "mmr"
    assert payload["max_output_count"] == 7
    assert signature["max_output_count"] == 7
    assert "monte_carlo" not in str(payload).lower()
    assert "debug" not in payload
    assert "debug" not in signature


def test_preset_rows_expose_mmr_and_maximum_limit():
    preset = get_preset("recommended")
    details = preset_detail_rows(preset)
    comparison = preset_comparison_table_rows()

    assert any(row["Pravidlo"] == "Finální výběr" and "MMR" in str(row["Hodnota"]) for row in details)
    assert all(row["selection"] == "deterministické MMR" for row in comparison)
    assert all("max" in row["max_output"] for row in comparison)


def test_export_bundle_contains_mmr_and_complete_config():
    result = _result(max_output_count=5)
    options = WebRunOptions(preset_key="recommended", max_output_count=5)

    bundle = build_export_bundle(result, options)

    assert "mmr_marginal_gain" in bundle.csv_text
    assert '"selection"' in bundle.candidates_json
    assert '"max_output_count": 5' in bundle.config_json
    assert "MMR portfolio výběr" in bundle.html_report
    assert bundle.zip_archive.startswith(b"PK")
