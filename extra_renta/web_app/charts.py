"""Altair grafy pro webovou aplikaci Extra Renta."""

from __future__ import annotations

from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st

from extra_renta.pipeline import PipelineResult
from extra_renta.web_app.service import (
    candidate_pool_score_histogram_rows,
    filter_throughput_rows,
    number_frequency_grid_rows,
    number_frequency_rows,
    pipeline_funnel_rows,
    score_histogram_rows,
    sensitivity_hint_rows,
    sum_histogram_rows,
)

_CHART_COLORS = {
    "blue": "#2f7cf6",
    "teal": "#26a69a",
    "orange": "#ff9f43",
    "violet": "#7c6cf3",
    "red": "#ef5350",
    "slate": "#516072",
    "light": "#d9e8ff",
}


def _configure(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_view(stroke=None)
        .configure_axis(
            labelFontSize=12,
            titleFontSize=14,
            titleFontWeight=700,
            labelColor="#435063",
            titleColor="#253246",
            gridColor="#e3e8ef",
            domainColor="#c2ccd8",
            tickColor="#c2ccd8",
            labelLimit=260,
        )
        .configure_legend(labelFontSize=12, titleFontSize=13)
        .configure_title(fontSize=17, color="#253246", anchor="start", fontWeight=800)
    )


def _horizontal_bar(
    df: pd.DataFrame,
    *,
    category: str,
    value: str,
    title: str,
    color: str,
    tooltip: list[str] | None = None,
    sort: str | list[str] = "-x",
) -> alt.Chart:
    base = alt.Chart(df).encode(
        y=alt.Y(f"{category}:N", sort=sort, title=None, axis=alt.Axis(labelLimit=300)),
        x=alt.X(f"{value}:Q", title=value, axis=alt.Axis(format=",d")),
        tooltip=tooltip or [category, alt.Tooltip(value, format=",d")],
    )
    bars = base.mark_bar(color=color, cornerRadiusEnd=6, size=22)
    labels = base.mark_text(align="left", baseline="middle", dx=6, color="#2f3440", fontSize=12).encode(
        text=alt.Text(f"{value}:Q", format=",d")
    )
    return _configure((bars + labels).properties(title=title, height=max(210, len(df) * 38)))


def _histogram_chart(df: pd.DataFrame, *, category: str, title: str, color: str) -> alt.Chart:
    base = alt.Chart(df).encode(
        x=alt.X(f"{category}:N", title=category, sort=None, axis=alt.Axis(labelAngle=0, labelOverlap=False)),
        y=alt.Y("Počet:Q", title="Počet kombinací", axis=alt.Axis(format=",d")),
        tooltip=[category, alt.Tooltip("Počet:Q", format=",d")],
    )
    bars = base.mark_bar(color=color, cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
    labels = base.mark_text(dy=-7, color="#353a3e", fontSize=11).encode(text=alt.Text("Počet:Q", format=",d"))
    return _configure((bars + labels).properties(title=title, height=320))


def _donut_chart(df: pd.DataFrame, *, title: str, color_range: list[str]) -> alt.Chart:
    pie = alt.Chart(df).mark_arc(innerRadius=48, outerRadius=78).encode(
        theta=alt.Theta("Hodnota:Q"),
        color=alt.Color("Kategorie:N", scale=alt.Scale(range=color_range), legend=alt.Legend(title=None)),
        tooltip=["Kategorie:N", alt.Tooltip("Hodnota:Q", format=",d")],
    )
    text = alt.Chart(df).mark_text(radius=102, fontSize=12, color="#253246").encode(
        theta=alt.Theta("Hodnota:Q"),
        text="Kategorie:N",
    )
    return _configure((pie + text).properties(title=title, height=240))


def render_pipeline_funnel(result: PipelineResult) -> None:
    rows = pipeline_funnel_rows(result.stats)
    st.subheader("Průchod kombinací zpracováním")
    st.caption("Každý řádek ukazuje počet kombinací, které zůstaly po dané fázi.")
    if not rows:
        st.caption("Bez dat není co vykreslit.")
        return
    df = pd.DataFrame(rows)
    order = list(df["Fáze"])
    chart = _horizontal_bar(
        df,
        category="Fáze",
        value="Počet",
        title="Zúžení prostoru kandidátů",
        color=_CHART_COLORS["blue"],
        tooltip=[
            "Fáze",
            alt.Tooltip("Počet:Q", format=",d"),
            alt.Tooltip("% z vygenerovaných:Q", format=".4f"),
            alt.Tooltip("% z celkového prostoru:Q", format=".6f"),
        ],
        sort=order,
    )
    st.altair_chart(chart, width="stretch")


def render_filter_rejections(result: PipelineResult) -> None:
    rows = filter_throughput_rows(result.stats)
    st.subheader("Vyřazení podle tvrdých filtrů")
    st.caption("Zamítnutí je přiřazeno prvnímu filtru, na kterém kombinace neprošla.")
    if not rows:
        st.caption("Tvrdé filtry v tomto běhu nezamítly žádnou kombinaci.")
        return
    df = pd.DataFrame(rows)
    chart = _horizontal_bar(
        df,
        category="Filtr",
        value="Zamítnuto",
        title="První důvod zamítnutí",
        color=_CHART_COLORS["orange"],
        tooltip=[
            "Filtr",
            alt.Tooltip("Zamítnuto:Q", format=",d"),
            alt.Tooltip("Zůstává:Q", format=",d"),
            alt.Tooltip("% ze zpracovaných:Q", format=".4f"),
        ],
    )
    st.altair_chart(chart, width="stretch")


def render_candidate_pool_score_distribution(
    result: PipelineResult,
    precomputed_rows: list[dict[str, object]] | None = None,
) -> None:
    rows = precomputed_rows if precomputed_rows is not None else candidate_pool_score_histogram_rows(result)
    st.subheader("Skóre kandidátního poolu")
    st.caption("Rozdělení skóre kombinací, ze kterých se sestavuje výsledné portfolio.")
    if rows:
        st.altair_chart(
            _histogram_chart(pd.DataFrame(rows), category="Skóre", title="Kandidátní pool podle skóre", color=_CHART_COLORS["teal"]),
            width="stretch",
        )
    else:
        st.caption("Kandidátní pool není v uloženém výsledku dostupný.")


def render_score_distribution(result: PipelineResult) -> None:
    rows = score_histogram_rows(result)
    st.subheader("Skóre výsledných kombinací")
    if rows:
        st.altair_chart(
            _histogram_chart(pd.DataFrame(rows), category="Skóre", title="Výsledné kombinace podle skóre", color=_CHART_COLORS["violet"]),
            width="stretch",
        )
    else:
        st.caption("Bez výsledných kombinací není co vykreslit.")


def render_sum_distribution(result: PipelineResult) -> None:
    rows = sum_histogram_rows(result)
    st.subheader("Součty výsledných kombinací")
    if rows:
        st.altair_chart(
            _histogram_chart(pd.DataFrame(rows), category="Součet", title="Rozdělení součtů", color=_CHART_COLORS["orange"]),
            width="stretch",
        )
    else:
        st.caption("Bez výsledných kombinací není co vykreslit.")


def render_number_frequency(result: PipelineResult) -> None:
    st.subheader("Zastoupení čísel ve výsledném portfoliu")
    rows = number_frequency_rows(result)
    if not rows:
        st.caption("Bez výsledných kombinací není co vykreslit.")
        return
    df = pd.DataFrame(rows)
    average = float(df["Četnost"].mean()) if not df.empty else 0.0
    base = alt.Chart(df).encode(
        x=alt.X("Číslo:O", title="Číslo", sort=list(range(1, 34)), axis=alt.Axis(labelAngle=0, labelOverlap=False)),
        y=alt.Y("Četnost:Q", title="Počet výskytů", axis=alt.Axis(format=",d")),
        tooltip=[alt.Tooltip("Číslo:O"), alt.Tooltip("Četnost:Q", format=",d")],
    )
    bars = base.mark_bar(color=_CHART_COLORS["blue"], cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
    labels = base.mark_text(dy=-6, color="#353a3e", fontSize=10).encode(text=alt.Text("Četnost:Q", format=",d"))
    rule = alt.Chart(pd.DataFrame({"Průměr": [average]})).mark_rule(color=_CHART_COLORS["red"], strokeDash=[6, 4], size=2).encode(
        y="Průměr:Q",
        tooltip=[alt.Tooltip("Průměr:Q", format=".2f")],
    )
    chart = _configure((bars + labels + rule).properties(title="Četnost čísel 1–33", height=350))
    st.altair_chart(chart, width="stretch")

    grid = pd.DataFrame(rows)
    grid["Řádek"] = ((grid["Číslo"] - 1) // 11) + 1
    grid["Pozice"] = ((grid["Číslo"] - 1) % 11) + 1
    heatmap = (
        alt.Chart(grid)
        .mark_rect(cornerRadius=5)
        .encode(
            x=alt.X("Pozice:O", title=None, axis=None),
            y=alt.Y("Řádek:O", title=None, axis=None),
            color=alt.Color(
                "Četnost:Q",
                scale=alt.Scale(range=["#f5f9ff", "#cfe0ff", _CHART_COLORS["blue"]]),
                legend=alt.Legend(title="Četnost"),
            ),
            tooltip=[alt.Tooltip("Číslo:Q", format="d"), alt.Tooltip("Četnost:Q", format=",d")],
        )
        .properties(title="Mřížka čísel", height=150)
    )
    text = (
        alt.Chart(grid)
        .mark_text(fontSize=13, fontWeight=700)
        .encode(x="Pozice:O", y="Řádek:O", text=alt.Text("Číslo:Q", format="d"), color=alt.value("#23272b"))
    )
    st.altair_chart(_configure(heatmap + text), width="stretch")

    with st.expander("Tabulka četností 1–33"):
        st.dataframe(pd.DataFrame(number_frequency_grid_rows(result)), width="stretch", hide_index=True)


def render_composition_donuts(result: PipelineResult) -> None:
    """Zobrazí jednoduché souhrnné kruhové grafy složení portfolia."""
    if not result.selected:
        return

    counts = Counter()
    low_high = Counter()
    for candidate in result.selected:
        counts["Sudá"] += candidate.metrics.even_count
        counts["Lichá"] += candidate.metrics.odd_count
        low_high["Nízká"] += candidate.metrics.low_count
        low_high["Vysoká"] += candidate.metrics.high_count

    col1, col2 = st.columns(2)
    with col1:
        df = pd.DataFrame([{"Kategorie": key, "Hodnota": value} for key, value in counts.items()])
        st.altair_chart(_donut_chart(df, title="Sudá vs. lichá čísla", color_range=[_CHART_COLORS["blue"], _CHART_COLORS["violet"]]), width="stretch")
    with col2:
        df = pd.DataFrame([{"Kategorie": key, "Hodnota": value} for key, value in low_high.items()])
        st.altair_chart(_donut_chart(df, title="Nízká vs. vysoká čísla", color_range=[_CHART_COLORS["teal"], _CHART_COLORS["orange"]]), width="stretch")


def render_sensitivity_hints(result: PipelineResult) -> None:
    st.subheader("Diagnostika pravidel")
    st.caption("Přehled ukazuje první zaznamenané důvody zamítnutí. Nejde o plnou ablační analýzu pravidel.")
    st.dataframe(pd.DataFrame(sensitivity_hint_rows(result)), width="stretch", hide_index=True)


def render_diversity_diagnostics(result: PipelineResult) -> None:
    st.subheader("Kvalita finálního výběru")
    diagnostics = result.stats.diversity_diagnostics
    cols = st.columns(3)
    cols[0].metric("Vybráno", f"{diagnostics.selected_count:,}".replace(",", " "))
    cols[1].metric("Průměrný MMR přínos", "-" if diagnostics.mmr_average_gain is None else f"{diagnostics.mmr_average_gain:.4f}")
    cols[2].metric("Přepočty kandidátů", f"{diagnostics.mmr_heap_recomputations:,}".replace(",", " "))


def render_all_charts(
    result: PipelineResult,
    *,
    candidate_pool_score_histogram: list[dict[str, object]] | None = None,
) -> None:
    overview, portfolio, rules = st.tabs(["Průchod a skóre", "Portfolio a čísla", "Pravidla a filtry"])
    with overview:
        render_pipeline_funnel(result)
        render_candidate_pool_score_distribution(result, candidate_pool_score_histogram)
        render_score_distribution(result)
        render_sum_distribution(result)
    with portfolio:
        render_number_frequency(result)
        render_composition_donuts(result)
        render_diversity_diagnostics(result)
    with rules:
        render_filter_rejections(result)
        render_sensitivity_hints(result)
