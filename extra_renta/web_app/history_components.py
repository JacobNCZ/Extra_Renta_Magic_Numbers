"""Streamlit komponenty pro bezpečnou aktualizaci historických tahů."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from extra_renta.combination_check import check_custom_combination
from extra_renta.history_update.models import FetchedDraw, HistoryUpdatePreview
from extra_renta.history_update.service import apply_history_update, fetch_history_update_preview
from extra_renta.history_update.source_names import source_page_name
from extra_renta.pipeline import PipelineResult
from extra_renta.presets import get_preset


_source_name = source_page_name


def _draw_rows(draws: tuple[FetchedDraw, ...] | list[FetchedDraw]) -> list[dict[str, object]]:
    return [
        {
            "Datum": draw.date,
            "Čísla": " ".join(f"{number:02d}" for number in draw.numbers),
            "Zdroj": _source_name(draw.source),
        }
        for draw in draws
    ]


def _render_draw_table(title: str, draws: tuple[FetchedDraw, ...]) -> None:
    st.markdown(f"**{title}: {len(draws)}**")
    if draws:
        st.dataframe(pd.DataFrame(_draw_rows(draws)), width="stretch", hide_index=True)


def render_history_preview(preview: HistoryUpdatePreview) -> None:
    """Zobrazí stručný náhled aktualizace historie."""
    st.write(f"Zdroj: **{_source_name(preview.source_url)}**")
    if preview.source_error:
        st.error("Zdroj historických tahů se nepodařilo načíst.")

    cols = st.columns(4)
    cols[0].metric("Staženo", len(preview.fetched_draws))
    cols[1].metric("Nové", len(preview.new_draws))
    cols[2].metric("Existující", len(preview.existing_draws))
    cols[3].metric("Konfliktní / nevalidní", len(preview.conflicting_draws) + len(preview.invalid_draws))

    _render_draw_table("Nové tahy", preview.new_draws)
    _render_draw_table("Konfliktní tahy", preview.conflicting_draws)
    _render_draw_table("Nevalidní tahy", preview.invalid_draws)


def _render_new_draw_comparison(
    preview: HistoryUpdatePreview,
    *,
    last_result: PipelineResult | None,
    candidate_pool_numbers: frozenset[tuple[int, ...]] | set[tuple[int, ...]] | None,
    candidate_pool_score_cutoff: float | None,
) -> None:
    """Porovná nově nalezené tahy s pravidly a výběrem posledního běhu."""
    if not preview.new_draws:
        return

    st.subheader("Porovnání nových tahů s posledním během")
    if last_result is None:
        st.info("Nejdříve spusť generování. Potom lze nové tahy porovnat s pravidly a finálním výběrem.")
        return

    st.caption(
        f"Porovnání používá předvolbu „{last_result.preset_label}“ a výsledek posledního dokončeného běhu."
    )
    config = get_preset(last_result.preset_key).config
    rows: list[dict[str, object]] = []
    checks = []
    for draw in preview.new_draws:
        check = check_custom_combination(
            " ".join(str(number) for number in draw.numbers),
            config=config,
            historical_context=last_result.historical_context,
            selected=last_result.selected,
            candidate_pool=None,
            candidate_pool_numbers=candidate_pool_numbers,
            candidate_pool_score_cutoff=candidate_pool_score_cutoff,
        )
        rows.append(
            {
                "Datum tahu": draw.date,
                "Kombinace": " ".join(f"{number:02d}" for number in draw.numbers),
                "Prošla pravidly": "Ano" if check.hard_filters_passed else "Ne",
                "Skóre": round(check.score.total_score, 2) if check.score else None,
                "V kandidátním poolu": (
                    "Ano" if check.in_candidate_pool else "Ne"
                ) if check.candidate_pool_membership_known else "Neuloženo",
                "Ve finálním výběru": "Ano" if check.in_final_selection else "Ne",
                "Pořadí": check.final_rank,
            }
        )
        checks.append((draw, check))

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        column_config={"Skóre": st.column_config.NumberColumn(format="%.2f")},
    )
    for draw, check in checks:
        with st.expander(f"Detail {draw.date}: {' '.join(f'{number:02d}' for number in draw.numbers)}"):
            st.write(check.reason)


def render_history_update_tab(
    *,
    last_result: PipelineResult | None = None,
    candidate_pool_numbers: frozenset[tuple[int, ...]] | set[tuple[int, ...]] | None = None,
    candidate_pool_score_cutoff: float | None = None,
) -> None:
    """Bezpečný tab pro kontrolu a volitelné uložení nové historie."""
    st.subheader("Aktualizace historických tahů")
    st.caption("Sekce porovná externí stránku s lokální historií. Zápis proběhne až po potvrzení.")

    if st.button("Zkontrolovat dostupné nové tahy"):
        with st.spinner("Kontroluji dostupné tahy..."):
            st.session_state["history_preview"] = fetch_history_update_preview()

    preview = st.session_state.get("history_preview")
    if preview is None:
        return

    render_history_preview(preview)
    _render_new_draw_comparison(
        preview,
        last_result=last_result,
        candidate_pool_numbers=candidate_pool_numbers,
        candidate_pool_score_cutoff=candidate_pool_score_cutoff,
    )

    can_apply = bool(preview.new_draws) and not preview.conflicting_draws and not preview.invalid_draws and not preview.source_error
    if not can_apply:
        st.caption("Zápis není dostupný, protože nejsou nové tahy nebo existuje konflikt, nevalidní data či chyba zdroje.")
        return

    confirm = st.checkbox("Potvrzuji uložení nových tahů do lokální historie a vytvoření zálohy.")
    if st.button("Uložit nové tahy do lokální historie", disabled=not confirm):
        result = apply_history_update(preview)
        if result.updated:
            st.success(result.message)
        else:
            st.warning(result.message)
