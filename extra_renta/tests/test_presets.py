from extra_renta.core.config_validation import validate_app_config
from extra_renta.presets import (
    PRESETS,
    format_preset_comparison_table,
    format_preset_detail,
    format_preset_menu,
    get_preset,
)


def test_all_expected_presets_exist():
    assert tuple(PRESETS) == ("recommended", "strict", "experimental_strict")


def test_strict_preset_is_stricter_than_recommended():
    recommended = get_preset("recommended").config
    strict = get_preset("strict").config

    assert strict.filters.sum_min >= recommended.filters.sum_min
    assert strict.filters.sum_max <= recommended.filters.sum_max
    assert set(strict.filters.allowed_odd_counts).issubset(recommended.filters.allowed_odd_counts)
    assert strict.scoring.min_score_to_keep > recommended.scoring.min_score_to_keep


def test_experimental_has_stricter_overlap_than_strict():
    strict = get_preset("strict").config
    experimental = get_preset("experimental_strict").config

    assert experimental.diversity.max_overlap_between_selected < strict.diversity.max_overlap_between_selected


def test_preset_detail_contains_maximum_limit_and_mmr_weights():
    preset = get_preset("recommended")
    detail = format_preset_detail(preset)

    assert preset.label in detail
    assert "Součet kombinace" in detail
    assert "Limit kandidátního poolu" in detail
    assert "Maximální limit výstupu" in detail
    assert "MMR váhy" in detail


def test_preset_menu_contains_mmr_pipeline_without_monte_carlo():
    menu = format_preset_menu()
    table = format_preset_comparison_table()

    assert "POROVNÁNÍ PŘEDVOLEB" in menu
    assert "filtry → scoring → MMR portfolio výběr" in menu
    assert "deterministické MMR" in table
    assert "Limit výstupu" in table
    assert "Monte Carlo" not in menu + table


def test_each_preset_has_normalized_mmr_weights():
    for preset in PRESETS.values():
        mmr = preset.config.mmr
        total = (
            mmr.score_weight
            + mmr.number_balance_weight
            + mmr.pair_coverage_weight
            + mmr.overlap_diversity_weight
            + mmr.pair_reuse_safety_weight
        )
        assert total == 1.0
        assert preset.config.diversity.max_output_count > 0


def test_all_presets_pass_config_validation():
    for preset in PRESETS.values():
        validation = validate_app_config(preset.config)
        assert validation.errors == ()
