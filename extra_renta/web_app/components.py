"""Znovupoužitelné Streamlit komponenty pro Extra Renta web."""

from __future__ import annotations

from html import escape
import re

import pandas as pd
import streamlit as st

from extra_renta.combination_check import check_custom_combination
from extra_renta.pipeline import PipelineResult
from extra_renta.presets import get_preset
from extra_renta.web_app.explanations import (
    FIXED_RUN_SUMMARY,
    FIXED_RUN_TITLE,
    PROCESS_STEPS,
    RULE_EXPLANATIONS,
    SCORE_EXPLANATION,
)
from extra_renta.web_app.service import (
    ExportBundle,
    SCORE_COMPONENT_LABELS,
    WebRunOptions,
    available_presets,
    build_export_bundle,
    candidate_detail_row,
    candidate_selection_reason,
    candidates_table_rows,
    candidates_technical_table_rows,
    filter_throughput_rows,
    preset_comparison_table_rows,
    preset_detail_rows,
    preset_options,
    result_summary,
    score_breakdown_rows,
)


def _format_int(value: int | float | None) -> str:
    if value is None:
        return "-"
    return f"{int(value):,}".replace(",", " ")


def _balls_html(numbers: tuple[int, ...] | list[int]) -> str:
    return "".join(f'<span class="er-ball">{int(number):02d}</span>' for number in numbers)


def _matching_brace(css: str, opening_index: int) -> int:
    depth = 0
    for index in range(opening_index, len(css)):
        if css[index] == "{":
            depth += 1
        elif css[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return len(css) - 1


def _scope_report_css(css: str, scope: str = ".er-inline-report") -> str:
    """Omezí CSS samostatného reportu na jeho kontejner, aby neovlivňovalo celé UI."""
    output: list[str] = []
    index = 0
    while index < len(css):
        opening = css.find("{", index)
        semicolon = css.find(";", index)
        if opening == -1:
            output.append(css[index:])
            break
        if semicolon != -1 and semicolon < opening and css[index:].lstrip().startswith("@"):
            output.append(css[index:semicolon + 1])
            index = semicolon + 1
            continue

        header = css[index:opening].strip()
        closing = _matching_brace(css, opening)
        body = css[opening + 1:closing]
        prefix_ws = css[index:opening - len(css[index:opening].lstrip())]

        if header.startswith("@media") or header.startswith("@supports"):
            output.append(f"{prefix_ws}{header}{{{_scope_report_css(body, scope)}}}")
        elif header.startswith("@keyframes") or header.startswith("@font-face"):
            output.append(f"{prefix_ws}{header}{{{body}}}")
        else:
            selectors: list[str] = []
            for raw_selector in header.split(","):
                selector = raw_selector.strip()
                if not selector:
                    continue
                if selector == ":root":
                    selectors.append(scope)
                elif selector in {"html", "body"}:
                    selectors.append(scope)
                elif selector.startswith("body "):
                    selectors.append(f"{scope} {selector[5:]}")
                elif selector.startswith("html "):
                    selectors.append(f"{scope} {selector[5:]}")
                elif selector.startswith(scope):
                    selectors.append(selector)
                else:
                    selectors.append(f"{scope} {selector}")
            output.append(f"{prefix_ws}{', '.join(selectors)}{{{body}}}")
        index = closing + 1
    return "".join(output)


def _extract_inline_report_html(html_report: str) -> str:
    """Vyjme z plného HTML reportu vnitřní obsah pro vložení přímo do stránky."""
    style_match = re.search(r"<style[^>]*>(.*?)</style>", html_report, re.S | re.I)
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html_report, re.S | re.I)
    scoped_style = ""
    if style_match:
        scoped_style = f"<style>{_scope_report_css(style_match.group(1))}</style>"
    body = body_match.group(1) if body_match else html_report
    return f'<div class="er-inline-report">{scoped_style}{body}</div>'


def render_intro_dashboard() -> None:
    """Krátký orientační přehled toku aplikace."""
    st.subheader("Jak probíhá zpracování")
    st.caption(FIXED_RUN_SUMMARY)
    cols = st.columns(3)
    for index, (title, text) in enumerate(PROCESS_STEPS):
        with cols[index % 3]:
            st.markdown(
                f'<div class="er-subtle-card"><strong>{escape(title)}</strong><br><span>{escape(text)}</span></div>',
                unsafe_allow_html=True,
            )


def render_fixed_run_info() -> None:
    """Zobrazí stručné informace o režimu výpočtu a základní informace o hře."""
    st.markdown(
        f"""
        <div class="er-inline-grid">
          <div class="er-subtle-card">
            <div class="er-section-label">Režim výpočtu</div>
            <strong>{escape(FIXED_RUN_TITLE)}</strong><br>
            <span>Kompletní průchod všech kombinací, filtrace, scoring a finální diverzifikovaný výběr.</span>
          </div>
          <div class="er-game-card">
            <div>
              <strong>Jak se hraje</strong>
              <span>V Extra Rentě se vybírá 7 čísel z rozsahu 1 až 33.</span>
            </div>
            <div>
              <strong>Losování</strong>
              <span>Standardně probíhá v pondělí a ve čtvrtek večer.</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_rule_explanations() -> None:
    """Zobrazí metodiku, pravidla a disclaimer mimo hlavní pracovní obrazovku."""
    st.subheader("Pravidla a metodika")
    st.caption("Technické vysvětlení filtrů, scoringu, MMR a významu historických dat.")

    with st.expander("Důležité vymezení projektu", expanded=True):
        st.markdown(
            "**Aplikace slouží pouze jako generátor kandidátních kombinací, filtrační systém, "
            "scoring engine, diverzifikační systém a reportingový nástroj.**"
        )
        st.write(
            "Historická data slouží pouze k analytickému porovnání. Aplikace negarantuje výhru "
            "ani vyšší matematickou pravděpodobnost výhry. Každá platná kombinace má v náhodném "
            "losování stejnou pravděpodobnost."
        )

    with st.expander(SCORE_EXPLANATION.title, expanded=True):
        st.markdown(f"**{SCORE_EXPLANATION.short}**")
        st.write(SCORE_EXPLANATION.detail)

    with st.expander("Jak funguje výpočetní režim", expanded=True):
        st.markdown(f"**{FIXED_RUN_TITLE}**")
        st.write(FIXED_RUN_SUMMARY)
        for title, text in PROCESS_STEPS:
            st.markdown(f"- **{title}:** {text}")

    for block in RULE_EXPLANATIONS:
        with st.expander(block.title):
            st.markdown(f"**{block.short}**")
            st.write(block.detail)


def render_preset_overview() -> None:
    """Zobrazí přehled pevných předvoleb s uživatelsky čitelnými názvy."""
    st.subheader("Předvolby nastavení")
    st.caption("Předvolba mění přísnost filtrů, scoringu a diverzifikace; samotný způsob běhu zůstává stejný.")
    for preset in available_presets():
        tag = {
            "recommended": "Doporučeno pro běžné použití",
            "strict": "Přísnější analytická varianta",
            "experimental_strict": "Experimentální a velmi přísné",
        }.get(preset.key, "")
        with st.expander(f"{preset.label} · {tag}", expanded=preset.key == "recommended"):
            st.write(preset.description)
            st.markdown("**Co nastavení ovlivňuje:**")
            for item in preset.rule_summary:
                st.markdown(f"- {item}")
            st.dataframe(pd.DataFrame(preset_detail_rows(preset)), width="stretch", hide_index=True)

    st.subheader("Porovnání předvoleb")
    st.dataframe(pd.DataFrame(preset_comparison_table_rows()), width="stretch", hide_index=True)


def render_sidebar() -> WebRunOptions:
    """Vykreslí zjednodušený postranní panel pouze s volbou předvolby."""
    st.sidebar.markdown('<div class="er-sidebar-brand">Extra Renta</div>', unsafe_allow_html=True)
    st.sidebar.caption("Analytický dashboard")

    current_state = st.session_state.get("vault_state", "closed")
    state_label = {
        "closed": "Připraveno",
        "generating": "Probíhá výpočet",
        "open": "Výsledky jsou připravené",
        "error": "Poslední běh selhal",
    }.get(current_state, "Připraveno")
    st.sidebar.markdown(
        f'<div class="er-sidebar-status"><strong>Stav aplikace</strong><br><small>{escape(state_label)}</small></div>',
        unsafe_allow_html=True,
    )

    labels = preset_options()
    preset_key = st.sidebar.selectbox(
        "Předvolba pravidel",
        options=list(labels.keys()),
        format_func=lambda key: labels[key],
        index=0,
        help="Předvolba nastavuje přísnost filtrů, scoringu a finálního výběru.",
    )
    preset = get_preset(preset_key)
    st.sidebar.caption(preset.description)
    st.sidebar.markdown("---")
    st.sidebar.caption("Generování spustíš jediným tlačítkem v hlavní záložce.")

    return WebRunOptions(
        preset_key=preset_key,
        max_output_count=None,
        export_outputs=False,
    )


def render_best_combination_preview(result: PipelineResult | None) -> None:
    """Vykreslí pravý náhledový panel s první výslednou kombinací."""
    if result is None or not result.selected:
        st.markdown(
            """
            <div class="er-preview-card">
              <div class="er-section-label">Výsledná kombinace</div>
              <h3>Zatím není k dispozici žádný výsledek</h3>
              <p>Po dokončení generování se zde zobrazí první pořadí a základní souhrn běhu.</p>
              <div class="er-preview-empty">
                <span>Připraveno na nový běh</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    best = result.selected[0]
    gain = "-" if best.selection is None else f"{best.selection.marginal_gain:.4f}"
    st.markdown(
        f"""
        <div class="er-preview-card">
          <div class="er-section-label">Výsledná kombinace</div>
          <h3>První pořadí aktuálního běhu</h3>
          <div class="er-balls er-balls-large">{_balls_html(best.numbers)}</div>
          <div class="er-preview-stats">
            <div><span>Skóre</span><strong>{best.score.total_score:.2f}</strong></div>
            <div><span>Přínos diverzity</span><strong>{gain}</strong></div>
            <div><span>Vybraných kombinací</span><strong>{result.stats.final_selected}</strong></div>
            <div><span>Doba běhu</span><strong>{result.stats.benchmark.total_seconds:.3f} s</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_quick_overview_cards(result: PipelineResult) -> None:
    """Zobrazí stručné doplňkové karty."""
    stats = result.stats
    st.markdown(
        f"""
        <div class="er-quick-grid">
          <div class="er-quick-card">
            <span class="er-quick-title">Výsledné kombinace</span>
            <strong>{stats.final_selected}</strong>
            <small>aktuální výstup</small>
          </div>
          <div class="er-quick-card">
            <span class="er-quick-title">Kandidátní pool</span>
            <strong>{stats.kept_for_diversity}</strong>
            <small>po filtrech a skóre</small>
          </div>
          <div class="er-quick-card">
            <span class="er-quick-title">Doba běhu</span>
            <strong>{stats.benchmark.total_seconds:.3f} s</strong>
            <small>poslední dokončený běh</small>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary(result: PipelineResult) -> None:
    """Zobrazí zjednodušené hlavní metriky běhu."""
    summary = result_summary(result)
    cols = st.columns(4)
    cols[0].metric("Zpracováno kombinací", _format_int(summary["Vygenerováno"]))
    cols[1].metric("Zůstatek po filtrech", _format_int(summary["Po tvrdých filtrech"]))
    cols[2].metric("Po aplikování skóre", _format_int(summary["Po minimálním skóre"]))
    cols[3].metric("Výsledné kombinace", _format_int(summary["Finálně vybráno"]))

    cols = st.columns(3)
    cols[0].metric("Kandidátní pool", _format_int(summary["Ponecháno pro MMR"]))
    cols[1].metric("MMR přepočty", _format_int(summary["MMR přepočty"]))
    cols[2].metric("Doba běhu", f"{summary['Čas celkem [s]']} s")

    for warning in result.stats.strictness_warnings:
        st.warning(warning)


def render_ball_results(result: PipelineResult, *, key_prefix: str = "results") -> None:
    """Zobrazí výsledné kombinace jako karty s loterijními kuličkami."""
    if not result.selected:
        st.warning("Nebyla vybrána žádná kombinace. Zkus mírnější předvolbu nebo filtry.")
        return

    choices = [10, 25, 50, 100]
    maximum = len(result.selected)
    valid_choices = [choice for choice in choices if choice < maximum] + [maximum]
    valid_choices = sorted(set(valid_choices))
    default_index = valid_choices.index(min(25, maximum)) if min(25, maximum) in valid_choices else 0
    if maximum <= 10:
        display_count = maximum
    else:
        display_count = st.selectbox(
            "Počet graficky zobrazených kombinací",
            options=valid_choices,
            index=default_index,
            help="Všechny výsledky zůstávají dostupné v tabulce a exportech.",
            key=f"{key_prefix}_ball_display_count",
        )

    cards: list[str] = ['<div class="er-results-grid">']
    for rank, candidate in enumerate(result.selected[: int(display_count)], start=1):
        card_class = "er-result-card is-first" if rank == 1 else "er-result-card"
        rank_label = "První pořadí" if rank == 1 else f"Pořadí {rank}"
        cards.append(
            f"""
            <article class="{card_class}">
              <div class="er-result-head">
                <span class="er-rank">{rank_label}</span>
              </div>
              <div class="er-balls">{_balls_html(candidate.numbers)}</div>
              <div class="er-result-meta">
                <span>Skóre <b>{candidate.score.total_score:.2f}</b></span>
                <span>Součet <b>{candidate.metrics.total_sum}</b></span>
                <span>Sudá / lichá <b>{candidate.metrics.even_count} / {candidate.metrics.odd_count}</b></span>
              </div>
            </article>
            """
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)


def render_results_table(result: PipelineResult, *, show_technical_columns: bool = False) -> None:
    rows = candidates_technical_table_rows(result) if show_technical_columns else candidates_table_rows(result)
    if not rows:
        return
    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        column_config={
            "Skóre": st.column_config.NumberColumn(format="%.2f"),
            "MMR přínos": st.column_config.NumberColumn(format="%.4f"),
            "Kombinace": st.column_config.TextColumn(width="medium"),
        },
    )


def render_candidate_details(result: PipelineResult) -> None:
    """Zobrazí detailní rozpad prvních kombinací."""
    if not result.selected:
        return
    st.subheader("Detail kombinací")
    st.caption("Rozbalovací detail ukazuje individuální skóre i přínos kombinace pro celé portfolio.")
    detail_limit = min(25, len(result.selected))
    for rank, candidate in enumerate(result.selected[:detail_limit], start=1):
        with st.expander(
            f"#{rank}: {' '.join(f'{number:02d}' for number in candidate.numbers)} · skóre {candidate.score.total_score:.2f}"
        ):
            st.markdown(f'<div class="er-balls">{_balls_html(candidate.numbers)}</div>', unsafe_allow_html=True)
            st.markdown("**Proč byla kombinace vybrána**")
            st.write(candidate_selection_reason(candidate))
            st.dataframe(pd.DataFrame([candidate_detail_row(candidate)]), width="stretch", hide_index=True)
            if candidate.score.notes:
                st.markdown("**Vysvětlení skóre**")
                for note in candidate.score.notes:
                    st.markdown(f"- {note}")
            st.markdown("**Rozpad skóre**")
            st.dataframe(pd.DataFrame(score_breakdown_rows(candidate)), width="stretch", hide_index=True)


def render_custom_combination_checker(
    result: PipelineResult,
    *,
    candidate_pool_numbers: frozenset[tuple[int, ...]] | set[tuple[int, ...]] | None = None,
    candidate_pool_score_cutoff: float | None = None,
) -> None:
    """Umožní porovnat vlastní kombinace s pravidly a posledním finálním výběrem."""
    st.subheader("Ověřit vlastní kombinace")
    st.caption(
        "Každou kombinaci zadej na samostatný řádek. Kontrola použije předvolbu a data posledního dokončeného běhu."
    )
    raw_text = st.text_area(
        "Kombinace k ověření",
        placeholder="3, 8, 12, 17, 21, 27, 32\n2, 7, 11, 18, 23, 29, 31",
        height=120,
        key="custom_combination_input",
    )
    if not st.button("Ověřit kombinace", width="stretch", key="check_custom_combinations_button"):
        return

    raw_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not raw_lines:
        st.warning("Zadej alespoň jednu kombinaci.")
        return

    config = get_preset(result.preset_key).config
    rows: list[dict[str, object]] = []
    details = []
    for raw_value in raw_lines:
        check = check_custom_combination(
            raw_value,
            config=config,
            historical_context=result.historical_context,
            selected=result.selected,
            candidate_pool=None,
            candidate_pool_numbers=candidate_pool_numbers,
            candidate_pool_score_cutoff=candidate_pool_score_cutoff,
        )
        rows.append({
            "Kombinace": " ".join(f"{number:02d}" for number in check.numbers) if check.numbers else raw_value,
            "Platný vstup": "Ano" if check.is_valid_input else "Ne",
            "Prošla pravidly": "Ano" if check.hard_filters_passed else "Ne",
            "Skóre": round(check.score.total_score, 2) if check.score else None,
            "Prošla minimálním skóre": "Ano" if check.passes_min_score else "Ne",
            "V kandidátním poolu": (
                "Ano" if check.in_candidate_pool else "Ne"
            ) if check.candidate_pool_membership_known else "Neuloženo",
            "Ve finálním výběru": "Ano" if check.in_final_selection else "Ne",
            "Pořadí": check.final_rank,
        })
        details.append(check)

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        column_config={"Skóre": st.column_config.NumberColumn(format="%.2f")},
    )
    for index, check in enumerate(details, start=1):
        label = " ".join(f"{number:02d}" for number in check.numbers) if check.numbers else check.raw_input
        with st.expander(f"Detail #{index}: {label}"):
            st.write(check.reason)
            if check.input_errors:
                for error in check.input_errors:
                    st.markdown(f"- {error}")
            if check.filter_result and check.filter_result.failed_filter:
                st.caption(f"První neprošlý filtr: {check.filter_result.failed_filter}")
            if check.score:
                st.dataframe(
                    pd.DataFrame([
                        {"Komponenta": SCORE_COMPONENT_LABELS.get(key, key), "Body": round(float(value), 3)}
                        for key, value in sorted(check.score.components.items())
                    ]),
                    width="stretch",
                    hide_index=True,
                )


def render_filter_table(result: PipelineResult) -> None:
    st.caption("Tabulka ukazuje první zaznamenaný filtr, na kterém byly kombinace zamítnuty.")
    st.dataframe(pd.DataFrame(filter_throughput_rows(result.stats)), width="stretch", hide_index=True)


def render_report_and_exports(
    result: PipelineResult,
    options: WebRunOptions,
    *,
    bundle: ExportBundle | None = None,
) -> ExportBundle:
    """Zobrazí HTML report přímo ve stránce a exporty v rozbalovací sekci."""
    bundle = bundle or build_export_bundle(result, options)
    st.markdown(_extract_inline_report_html(bundle.html_report), unsafe_allow_html=True)

    with st.expander("Možnosti stažení a exportu", expanded=False):
        col1, col2 = st.columns(2)
        col1.download_button(
            "Stáhnout HTML report",
            bundle.html_report,
            file_name="extra_renta_report.html",
            mime="text/html",
            width="stretch",
        )
        col2.download_button(
            "Stáhnout kompletní ZIP",
            bundle.zip_archive,
            file_name="extra_renta_exporty.zip",
            mime="application/zip",
            width="stretch",
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.download_button(
            "CSV výsledků",
            bundle.csv_text,
            file_name="extra_renta_candidates.csv",
            mime="text/csv",
            width="stretch",
        )
        col2.download_button(
            "JSON výsledků",
            bundle.candidates_json,
            file_name="extra_renta_candidates.json",
            mime="application/json",
            width="stretch",
        )
        col3.download_button(
            "JSON konfigurace",
            bundle.config_json,
            file_name="extra_renta_config.json",
            mime="application/json",
            width="stretch",
        )
        col4.download_button(
            "JSON statistik",
            bundle.stats_json,
            file_name="extra_renta_stats.json",
            mime="application/json",
            width="stretch",
        )
    return bundle


def render_export_buttons(result: PipelineResult, options: WebRunOptions) -> ExportBundle:
    """Kompatibilní alias pro starší volání."""
    return render_report_and_exports(result, options)
