"""Streamlit komponenty pro historii prvních míst z dokončených běhů."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from extra_renta.web_app.run_history import (
    clear_first_place_history,
    delete_first_place_run,
    first_place_history_csv,
    get_first_place_run,
    history_database_path,
    list_first_place_runs,
)


def _render_saved_balls(numbers: list[int]) -> None:
    balls = "".join(f'<span class="er-ball">{number:02d}</span>' for number in numbers)
    st.markdown(f'<div class="er-balls">{balls}</div>', unsafe_allow_html=True)


def render_first_place_history_tab() -> None:
    """Zobrazí tabulku uložených prvních kombinací, detail a správu historie."""
    st.subheader("Historie prvních míst")
    st.caption(
        "Po každém úspěšném generování se automaticky uloží kombinace na prvním místě, "
        "její skóre, MMR přínos, nastavení a souhrn běhu. Data se ukládají lokálně do SQLite."
    )

    rows = list_first_place_runs()
    if not rows:
        st.info("Historie je zatím prázdná. První záznam vznikne po dokončení generování.")
        st.caption(f"Databáze: {history_database_path()}")
        return

    visible_rows = [{key: value for key, value in row.items() if key != "ID běhu"} for row in rows]
    st.dataframe(
        pd.DataFrame(visible_rows),
        width="stretch",
        hide_index=True,
        column_config={
            "Skóre": st.column_config.NumberColumn(format="%.3f"),
            "MMR přínos": st.column_config.NumberColumn(format="%.5f"),
            "Čas [s]": st.column_config.NumberColumn(format="%.3f"),
        },
    )

    with st.expander("Detail uloženého běhu", expanded=False):
        labels = {
            row["ID běhu"]: f"{row['Datum a čas']} · {row['Předvolba']} · {row['První kombinace']}"
            for row in rows
        }
        selected_id = st.selectbox(
            "Vyber uložený běh",
            options=list(labels),
            format_func=lambda value: labels[value],
            key="first_place_history_detail_id",
        )
        detail = get_first_place_run(selected_id)
        if detail is not None:
            candidate = detail["candidate"]
            _render_saved_balls([int(number) for number in candidate["numbers"]])
            cols = st.columns(4)
            cols[0].metric("Skóre", f"{float(candidate['score']):.3f}")
            selection = candidate.get("selection") or {}
            cols[1].metric("MMR přínos", f"{float(selection.get('marginal_gain', 0.0)):.5f}")
            cols[2].metric("Nové páry", str(selection.get("new_pairs", "-")))
            cols[3].metric("Předvolba", str(detail["preset_label"]))

            detail_tabs = st.tabs(["Souhrn", "Kandidát", "Konfigurace"])
            with detail_tabs[0]:
                st.dataframe(pd.DataFrame([detail["summary"]]), width="stretch", hide_index=True)
            with detail_tabs[1]:
                st.json(candidate, expanded=False)
            with detail_tabs[2]:
                st.json(detail["config"], expanded=False)

    with st.expander("Export a správa historie", expanded=False):
        csv_text = first_place_history_csv()
        st.download_button(
            "Stáhnout historii jako CSV",
            csv_text,
            file_name="extra_renta_historie_prvnich_mist.csv",
            mime="text/csv",
            width="stretch",
        )
        st.caption(f"Lokální databáze: {history_database_path()}")

        delete_col, clear_col = st.columns(2)
        delete_id = delete_col.selectbox(
            "Záznam ke smazání",
            options=[row["ID běhu"] for row in rows],
            format_func=lambda value: labels[value],
            key="first_place_history_delete_id",
        )
        if delete_col.button(
            "Smazat vybraný záznam",
            width="stretch",
        ) and delete_first_place_run(delete_id):
            st.success("Vybraný záznam byl smazán.")
            st.rerun()

        confirm_clear = clear_col.checkbox("Potvrzuji smazání celé historie", key="confirm_clear_first_place_history")
        if clear_col.button("Smazat celou historii", disabled=not confirm_clear, width="stretch"):
            removed = clear_first_place_history()
            st.success(f"Smazáno záznamů: {removed}")
            st.rerun()
