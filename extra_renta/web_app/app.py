"""Streamlit aplikace Extra Renta.

Spuštění z kořene projektu:
    python -m streamlit run extra_renta/web_app/app.py
"""

from __future__ import annotations

import logging

import streamlit as st

from extra_renta.web_app.charts import render_all_charts
from extra_renta.web_app.components import (
    render_ball_results,
    render_best_combination_preview,
    render_custom_combination_checker,
    render_filter_table,
    render_preset_overview,
    render_quick_overview_cards,
    render_report_and_exports,
    render_results_table,
    render_rule_explanations,
    render_sidebar,
    render_summary,
)
from extra_renta.web_app.history_components import render_history_update_tab
from extra_renta.web_app.run_history import save_first_place_run
from extra_renta.web_app.run_history_components import render_first_place_history_tab
from extra_renta.web_app.service import (
    build_export_bundle,
    candidate_pool_number_snapshot,
    candidate_pool_score_cutoff,
    candidate_pool_score_histogram_rows,
    options_signature,
    run_web_generation,
    strip_candidate_pool,
)
from extra_renta.web_app.mechanical_counter import render_mechanical_counter
from extra_renta.web_app.styles import apply_global_styles, render_hero
from extra_renta.web_app.vault_state import (
    ERROR,
    GENERATING,
    OPEN,
    initialise_vault,
    reset_vault_for_configuration,
    set_vault_state,
)

LOGGER = logging.getLogger(__name__)

st.set_page_config(
    page_title="Extra Renta – Analytický generátor kombinací",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _generation_progress_callback(progress_bar, status_placeholder):
    def callback(done: int, total: int, stats) -> None:
        ratio = min(1.0, done / total) if total else 0.0
        progress_bar.progress(ratio)
        status_placeholder.caption(
            (
                f"Kontrola kombinací: {done:,} / {total:,} · "
                f"po filtrech {stats.passed_hard_filters:,} · po skóre {stats.passed_min_score:,}"
            ).replace(",", " ")
        )

    return callback


def _selection_progress_callback(progress_bar, status_placeholder):
    def callback(done: int, total: int) -> None:
        ratio = min(1.0, done / total) if total else 0.0
        progress_bar.progress(ratio)
        status_placeholder.caption(
            f"Sestavuji MMR portfolio: {done:,} / maximálně {total:,} kombinací".replace(",", " ")
        )

    return callback


def _result_is_stale(current_signature: dict[str, object]) -> bool:
    last_signature = st.session_state.get("last_options_signature")
    return last_signature is not None and last_signature != current_signature


def _render_stale_result_warning() -> None:
    st.warning(
        "Nastavení se od posledního běhu změnilo. Zobrazené výsledky patří k předchozí konfiguraci."
    )


def _execute_generation(options, current_signature, counter_placeholder) -> None:
    """Spustí pipeline, uloží výsledek a první pořadí do lokální historie."""
    set_vault_state(
        st.session_state,
        GENERATING,
        "Kontroluji kandidátní kombinace, počítám skóre a sestavuji portfolio…",
    )
    with counter_placeholder.container():
        render_mechanical_counter(GENERATING, st.session_state["vault_message"])

    progress_col, selection_col = st.columns(2)
    with progress_col:
        st.markdown("**1. Filtrace a scoring**")
        progress_bar = st.progress(0.0)
        status_placeholder = st.empty()
    with selection_col:
        st.markdown("**2. MMR portfolio výběr**")
        selection_progress_bar = st.progress(0.0)
        selection_status_placeholder = st.empty()

    try:
        with st.spinner("Probíhá kompletní výpočet…"):
            result = run_web_generation(
                options,
                progress_callback=_generation_progress_callback(progress_bar, status_placeholder),
                selection_progress_callback=_selection_progress_callback(
                    selection_progress_bar, selection_status_placeholder
                ),
            )

        progress_bar.progress(1.0)
        selection_progress_bar.progress(1.0)
        status_placeholder.caption("Filtrace a scoring dokončeny.")
        selection_status_placeholder.caption("MMR portfolio bylo sestaveno.")

        st.session_state["last_candidate_pool_score_histogram"] = candidate_pool_score_histogram_rows(result)
        st.session_state["last_candidate_pool_numbers"] = candidate_pool_number_snapshot(result)
        st.session_state["last_candidate_pool_score_cutoff"] = candidate_pool_score_cutoff(result)
        st.session_state["last_export_bundle"] = build_export_bundle(result, options)
        st.session_state["last_result"] = strip_candidate_pool(result)
        st.session_state["last_options"] = options
        st.session_state["last_options_signature"] = current_signature

        try:
            record_id = save_first_place_run(result, options)
            st.session_state["last_history_record_id"] = record_id
        except Exception:  # noqa: BLE001 - chyba historie nesmí znehodnotit dokončený běh
            LOGGER.exception("Nepodařilo se uložit první pořadí do historie")
            st.session_state["last_history_record_id"] = None
            st.warning("Výsledek byl dokončen, ale první pořadí se nepodařilo uložit do lokální historie.")

        set_vault_state(
            st.session_state,
            OPEN,
            "Výpočet je dokončený a výsledky jsou připravené.",
        )
        with counter_placeholder.container():
            render_mechanical_counter(
                OPEN,
                st.session_state["vault_message"],
                final_numbers=(result.selected[0].numbers if result.selected else None),
                result_count=result.stats.final_selected,
            )
        st.success("Generování, MMR výběr a příprava reportu byly dokončeny.")
    except Exception:  # noqa: BLE001 - technický detail patří do logu, ne do UI
        LOGGER.exception("Webové generování selhalo")
        set_vault_state(
            st.session_state,
            ERROR,
            "Běh se nepodařilo dokončit. Nastavení lze upravit a generování zopakovat.",
        )
        with counter_placeholder.container():
            render_mechanical_counter(ERROR, st.session_state["vault_message"])
        st.error("Běh se nepodařilo dokončit. Podrobnosti byly zapsány do interního logu.")


def main() -> None:
    apply_global_styles()
    initialise_vault(st.session_state)
    render_hero()

    options = render_sidebar()
    current_signature = options_signature(options)
    reset_vault_for_configuration(st.session_state, current_signature)

    tabs = st.tabs(
        [
            "Generování",
            "Výsledky",
            "Analýza",
            "Report a historie",
            "Nastavení a data",
        ]
    )

    with tabs[0]:
        st.subheader("Generování kandidátních kombinací")
        left_col, right_col = st.columns([1.2, 1.0], gap="large")
        with left_col:
            counter_placeholder = st.empty()
            with counter_placeholder.container():
                current_result = st.session_state.get("last_result")
                first_numbers = (
                    current_result.selected[0].numbers
                    if current_result is not None and current_result.selected
                    else None
                )
                render_mechanical_counter(
                    st.session_state["vault_state"],
                    st.session_state["vault_message"],
                    final_numbers=first_numbers,
                    result_count=(current_result.stats.final_selected if current_result is not None else None),
                )
            run_clicked = st.button(
                "Spustit generování",
                type="primary",
                disabled=st.session_state["vault_state"] == GENERATING,
                width="stretch",
                key="main_run_button",
            )
        with right_col:
            result = st.session_state.get("last_result")
            if result is None:
                render_best_combination_preview(None)
            else:
                if _result_is_stale(current_signature):
                    _render_stale_result_warning()
                render_best_combination_preview(result)
                render_quick_overview_cards(result)

        if run_clicked:
            _execute_generation(options, current_signature, counter_placeholder)
            result = st.session_state.get("last_result")

        result = st.session_state.get("last_result")
        if result is not None:
            if _result_is_stale(current_signature):
                _render_stale_result_warning()
            render_summary(result)
            st.markdown("### První pořadí")
            first_only = type(result)(
                selected=result.selected[:1],
                stats=result.stats,
                historical_context=result.historical_context,
                preset_key=result.preset_key,
                preset_label=result.preset_label,
                candidate_pool=None,
                combination_check=result.combination_check,
            )
            render_ball_results(first_only, key_prefix="generation_first")
        else:
            st.caption("Po dokončení generování se zde zobrazí souhrn a první výsledná kombinace.")

    with tabs[1]:
        result = st.session_state.get("last_result")
        if result is None:
            st.info("Nejdříve spusť generování.")
        else:
            if _result_is_stale(current_signature):
                _render_stale_result_warning()
            st.subheader("Výsledné kombinace")
            render_ball_results(result, key_prefix="results")
            with st.expander("Tabulkové zobrazení všech kombinací", expanded=False):
                render_results_table(result, show_technical_columns=False)
            st.divider()
            render_custom_combination_checker(
                result,
                candidate_pool_numbers=st.session_state.get("last_candidate_pool_numbers"),
                candidate_pool_score_cutoff=st.session_state.get("last_candidate_pool_score_cutoff"),
            )

    with tabs[2]:
        result = st.session_state.get("last_result")
        if result is None:
            st.info("Grafy budou dostupné po dokončení generování.")
        else:
            if _result_is_stale(current_signature):
                _render_stale_result_warning()
            st.subheader("Analýza a grafy")
            render_all_charts(
                result,
                candidate_pool_score_histogram=st.session_state.get("last_candidate_pool_score_histogram"),
            )
            with st.expander("Propustnost tvrdých filtrů – tabulka"):
                render_filter_table(result)

    with tabs[3]:
        result = st.session_state.get("last_result")
        last_options = st.session_state.get("last_options")
        report_tab, history_tab = st.tabs(["Report", "Historie prvních míst"])
        with report_tab:
            if result is None or last_options is None:
                st.info("HTML report a exporty budou dostupné po dokončení generování.")
            else:
                if _result_is_stale(current_signature):
                    _render_stale_result_warning()
                render_report_and_exports(
                    result,
                    last_options,
                    bundle=st.session_state.get("last_export_bundle"),
                )
        with history_tab:
            render_first_place_history_tab()

    with tabs[4]:
        presets_tab, rules_tab, history_data_tab = st.tabs(
            ["Předvolby", "Pravidla a metodika", "Historická data"]
        )
        with presets_tab:
            render_preset_overview()
        with rules_tab:
            render_rule_explanations()
        with history_data_tab:
            render_history_update_tab(
                last_result=st.session_state.get("last_result"),
                candidate_pool_numbers=st.session_state.get("last_candidate_pool_numbers"),
                candidate_pool_score_cutoff=st.session_state.get("last_candidate_pool_score_cutoff"),
            )


if __name__ == "__main__":
    main()
