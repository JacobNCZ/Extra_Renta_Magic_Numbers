"""HTML report po běhu Extra Renta pipeline."""

from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from string import Template

from ..core.models import AppConfig, CombinationCandidate, HistoricalContext, NumberTuple, RunStats
from ..core.score_explainer import explain_score_components
from ..presets import preset_comparison_rows
from .printer import build_next_step_recommendation
from .serialization import FILTER_EXPORT_LABELS, HARD_FILTER_EXPORT_ORDER, ensure_parent, format_int, score_max_points

_TEMPLATE_PATH = Path(__file__).with_name("templates") / "report.html"
_CSS_PATH = Path(__file__).with_name("static") / "report.css"

_SCORE_COMPONENT_HELP: dict[str, str] = {
    "sum_balance": "Hodnotí, jak blízko je součet kombinace ideálnímu součtu z konfigurace.",
    "odd_even_balance": "Hodnotí vyváženost sudých a lichých čísel.",
    "low_high_balance": "Hodnotí poměr nízkých a vysokých čísel podle zvolené předvolby.",
    "tier_balance": "Hodnotí rozložení do širších číselných pásem.",
    "bucket_balance": "Hodnotí rozložení do jemnějších číselných pásem.",
    "span_balance": "Hodnotí rozpětí mezi nejnižším a nejvyšším číslem.",
    "gap_balance": "Hodnotí mezery mezi sousedními čísly. Nejde o predikci losování.",
    "historical_similarity": "Pouze omezuje kopírování historických tahů; nezvyšuje pravděpodobnost výhry.",
    "pattern_safety": "Hodnotí, zda kombinace nepůsobí jako příliš jednoduchý lidský vzor.",
    "overall_uniformity": "Doplňkové skóre celkové vyváženosti kombinace.",
}


def _resource_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _funnel_svg(stats: RunStats) -> str:
    """Vrátí SVG funnel graf zúžení prostoru kombinací."""
    rows = [
        ("Vygenerováno", stats.generated),
        ("Po tvrdých filtrech", stats.passed_hard_filters),
        ("Po minimálním skóre", stats.passed_min_score),
        ("Kandidátní pool", stats.kept_for_diversity),
        ("Finální výběr", stats.final_selected),
    ]
    max_value = max((value for _, value in rows), default=1) or 1
    width = 900
    height = 86 + len(rows) * 56
    max_bar_width = 610
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Funnel graf zúžení kombinací">']
    parts.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    parts.append('<text x="20" y="30" font-size="17" font-weight="700" fill="#2f3438">Průchod kombinací přes pipeline</text>')
    for idx, (label, value) in enumerate(rows):
        y = 62 + idx * 56
        ratio = value / max_value if max_value else 0
        bar_width = max(8, int(ratio * max_bar_width)) if value else 4
        pct = (value / stats.generated * 100) if stats.generated else 0.0
        parts.append(f'<text x="20" y="{y + 15}" font-size="13" fill="#5f676d">{html.escape(label)}</text>')
        parts.append(f'<rect x="185" y="{y}" width="{bar_width}" height="24" rx="12" fill="#4b5156"/>')
        parts.append(f'<text x="{min(805, 200 + bar_width)}" y="{y + 16}" font-size="13" fill="#2f3438">{format_int(value)} · {pct:.3f} %</text>')
    parts.append('</svg>')
    return ''.join(parts)


def _number_frequency_svg(candidates: list[CombinationCandidate], config: AppConfig) -> str:
    """Vrátí SVG graf četnosti čísel ve finálním výběru."""
    counts = Counter(number for candidate in candidates for number in candidate.numbers)
    numbers = list(range(config.generator.number_min, config.generator.number_max + 1))
    max_count = max((counts[number] for number in numbers), default=1) or 1
    width = 900
    height = 260
    left = 35
    bottom = 215
    bar_gap = 3
    bar_width = max(10, int((width - left - 20) / len(numbers)) - bar_gap)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Četnost čísel ve finálním výběru">']
    parts.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    parts.append('<line x1="35" y1="215" x2="880" y2="215" stroke="#aeb5ba"/>')
    for idx, number in enumerate(numbers):
        count = counts[number]
        height_px = int((count / max_count) * 170) if max_count else 0
        x = left + idx * (bar_width + bar_gap)
        y = bottom - height_px
        parts.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{height_px}" fill="#6e757a">'
            f'<title>Číslo {number}: {count} výskytů</title></rect>'
        )
        if number % 2 == 1:
            parts.append(f'<text x="{x}" y="238" font-size="10" fill="#222">{number}</text>')
    parts.append('</svg>')
    return ''.join(parts)


def _filter_throughput_html(stats: RunStats) -> str:
    """Vrátí HTML tabulku propustnosti tvrdých filtrů."""
    rows: list[str] = []
    for row in stats.filter_throughput(HARD_FILTER_EXPORT_ORDER):
        rejected = int(row["rejected"])
        filter_name = str(row["filter"])
        label = FILTER_EXPORT_LABELS.get(filter_name, filter_name)
        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td>{format_int(rejected)}</td>"
            f"<td>{format_int(int(row['passed_after_filter']))}</td>"
            f"<td>{float(row['passed_after_filter_pct_of_generated']):.4f} %</td>"
            "</tr>"
        )
    return "".join(rows)


def _strictness_html(stats: RunStats) -> str:
    if not stats.strictness_warnings:
        return "<li>Kontrola přísnosti nebyla vyhodnocena.</li>"
    return "".join(f"<li>{html.escape(message)}</li>" for message in stats.strictness_warnings)


def _score_badge(score: float) -> str:
    """Vrátí HTML badge pro skóre kandidáta."""
    if score >= 90:
        label = "výborné"
        css = "excellent"
    elif score >= 75:
        label = "dobré"
        css = "good"
    else:
        label = "prošlo"
        css = "ok"
    return f'<span class="score-badge {css}">{score:.2f} · {label}</span>'


def _balls_html(numbers: NumberTuple) -> str:
    """Vrátí čísla jako vizuální kuličky pro HTML report."""
    return "".join(f'<span class="ball">{number:02d}</span>' for number in numbers)


def _candidate_reason(candidate: CombinationCandidate, config: AppConfig) -> str:
    """Vrátí krátké vysvětlení individuálního skóre a MMR přínosu."""
    selection = candidate.selection
    if selection is not None:
        return (
            f"MMR přínos {selection.marginal_gain:.3f}; "
            f"nové páry {selection.new_pairs}; "
            f"vyváženost čísel {selection.number_balance:.3f}."
        )

    weights = score_max_points(config)
    strong_components: list[str] = []
    for item in explain_score_components(candidate):
        key = str(item["key"])
        max_points = float(weights.get(key, 0.0))
        points = float(item["points"])
        if max_points and points / max_points >= 0.85:
            strong_components.append(str(item["label"]))
    if not strong_components:
        return "Kombinace prošla filtry a splnila minimální individuální skóre."
    return "Silné stránky skóre: " + ", ".join(strong_components[:3]) + "."

def _score_details_html(candidate: CombinationCandidate, config: AppConfig) -> str:
    """Vrátí sbalitelný HTML rozpad skóre pro jednu kombinaci."""
    rows: list[str] = []
    weights = score_max_points(config)
    for item in explain_score_components(candidate):
        key = str(item["key"])
        label = html.escape(str(item["label"]))
        help_text = html.escape(_SCORE_COMPONENT_HELP.get(key, "Scoringová komponenta podle zvolené konfigurace."))
        points = float(item["points"])
        max_points = float(weights.get(key, 0.0))
        pct = (points / max_points * 100) if max_points else 0.0
        rows.append(
            "<tr>"
            f'<td title="{help_text}">{label}</td>'
            f"<td>{points:.2f}</td>"
            f"<td>{max_points:.2f}</td>"
            f"<td>{pct:.0f} %</td>"
            "</tr>"
        )
    return (
        '<details class="score-details">'
        '<summary>Zobrazit rozpad skóre</summary>'
        '<table class="inner-table">'
        '<tr><th>Komponenta</th><th>Body</th><th>Maximum</th><th>Využití</th></tr>'
        f"{''.join(rows)}"
        '</table>'
        '</details>'
    )


def _first_candidate_html(candidates: list[CombinationCandidate], config: AppConfig) -> str:
    """Vrátí zvýrazněnou kartu kombinace na prvním místě."""
    if not candidates:
        return '<div class="empty-state">V tomto běhu nebyla vybrána žádná kombinace.</div>'
    candidate = candidates[0]
    selection = candidate.selection
    gain = "-" if selection is None else f"{selection.marginal_gain:.4f}"
    new_pairs = "-" if selection is None else str(selection.new_pairs)
    return (
        '<div class="first-place-card">'
        '<div class="eyebrow">První pořadí tohoto běhu</div>'
        f'<div class="first-balls">{_balls_html(candidate.numbers)}</div>'
        '<div class="first-place-metrics">'
        f'<span><small>Skóre</small><strong>{candidate.score.total_score:.2f}</strong></span>'
        f'<span><small>MMR přínos</small><strong>{gain}</strong></span>'
        f'<span><small>Nové páry</small><strong>{new_pairs}</strong></span>'
        f'<span><small>Součet</small><strong>{candidate.metrics.total_sum}</strong></span>'
        '</div>'
        f'<p>{html.escape(_candidate_reason(candidate, config))}</p>'
        '</div>'
    )


def _candidate_rows(candidates: list[CombinationCandidate], config: AppConfig) -> str:
    rows: list[str] = []
    for rank, candidate in enumerate(candidates[:100], start=1):
        rows.append(
            "<tr>"
            f"<td>{rank}</td>"
            f"<td class=\"numbers-cell\">{_balls_html(candidate.numbers)}</td>"
            f"<td>{_score_badge(candidate.score.total_score)}</td>"
            f"<td>{candidate.metrics.total_sum}</td>"
            f"<td>{candidate.metrics.odd_count}/{candidate.metrics.even_count}</td>"
            f"<td>{candidate.metrics.span}</td>"
            f"<td>{html.escape(_candidate_reason(candidate, config))}</td>"
            f"<td>{_score_details_html(candidate, config)}</td>"
            "</tr>"
        )
    return "".join(rows)


def _status_panel(stats: RunStats, config: AppConfig, preset_label: str) -> str:
    limit = config.diversity.max_output_count
    if stats.final_selected <= 0:
        status_class = "danger"
        status_label = "NIC NEPROŠLO"
    elif stats.final_selected >= limit:
        status_class = "ok"
        status_label = "DOSAŽEN LIMIT"
    else:
        status_class = "ok"
        status_label = "PLATNÝ VÝSLEDEK"

    selected_ratio = f"{stats.final_selected} / max {limit}"
    return (
        f'<div class="status-box {status_class}"><div class="label">Výsledek běhu</div><div class="value">{status_label}</div></div>'
        f'<div class="status-box"><div class="label">Předvolba</div><div class="value">{html.escape(preset_label)}</div></div>'
        f'<div class="status-box"><div class="label">Finální výběr</div><div class="value">{html.escape(selected_ratio)}</div></div>'
    )

def _recommendation_html(stats: RunStats, config: AppConfig) -> str:
    """Vrátí zvýrazněné doporučení dalšího kroku pro HTML report."""
    limit = config.diversity.max_output_count
    recommendation = build_next_step_recommendation(stats, limit)
    css = "danger" if stats.final_selected <= 0 else "ok"
    return (
        f'<div class="recommendation {css}">'
        f'<strong>Doporučený další krok:</strong> {html.escape(recommendation)}'
        '</div>'
    )

def _bottlenecks_html(stats: RunStats) -> str:
    """Vrátí HTML souhrn největších brzd filtrů a diverzifikace."""
    filter_items = sorted(stats.failed_by_filter.items(), key=lambda item: item[1], reverse=True)[:5]
    if filter_items:
        filter_rows = "".join(
            f"<li>{html.escape(FILTER_EXPORT_LABELS.get(name, name))}: <strong>{format_int(count)}</strong></li>"
            for name, count in filter_items
        )
    else:
        filter_rows = "<li>Tvrdé filtry v tomto běhu nezamítly žádnou kombinaci.</li>"

    diagnostics = stats.diversity_diagnostics
    diversity_items = [
        ("Překryv čísel mezi kandidáty", diagnostics.rejected_overlap),
        ("Opakování dvojic", diagnostics.rejected_pair_reuse),
        ("Opakování trojic", diagnostics.rejected_triplet_reuse),
    ]
    diversity_rows = "".join(
        f"<li>{html.escape(name)}: <strong>{format_int(count)}</strong></li>"
        for name, count in sorted(diversity_items, key=lambda item: item[1], reverse=True)
    )
    return (
        "<h3>Nejvíce vyřazovaly tvrdé filtry</h3>"
        f'<ol class="bottleneck-list">{filter_rows}</ol>'
        "<h3>Největší brzdy diverzifikace</h3>"
        f'<ol class="bottleneck-list">{diversity_rows}</ol>'
    )



def _preset_comparison_html(active_preset_key: str) -> str:
    """Vrátí statickou HTML tabulku porovnání předvoleb."""
    rows: list[str] = []
    for item in preset_comparison_rows():
        active = " active" if item["key"] == active_preset_key else ""
        rows.append(
            f'<tr class="preset-row{active}">'
            f'<td>{html.escape(item["label"])}</td>'
            f'<td>{html.escape(item["strictness"])}</td>'
            f'<td>{html.escape(item["sum_range"])}</td>'
            f'<td>{html.escape(item["min_score"])}</td>'
            f'<td>{html.escape(item["diversity_overlap"])}</td>'
            f'<td>{html.escape(item["pair_triplet"])}</td>'
            f'<td>{html.escape(item["selection"])}</td>'
            f'<td>{html.escape(item["max_output"])}</td>'
            '</tr>'
        )
    return (
        '<table class="preset-comparison">'
        '<tr><th>Předvolba</th><th>Přísnost</th><th>Součet</th><th>Min. skóre</th>'
        '<th>Překryv finálních</th><th>Páry / trojice</th><th>Výběr</th><th>Limit</th></tr>'
        f'{"".join(rows)}'
        '</table>'
        '<p class="small">Tabulka porovnává filtry, scoring a portfolio výběr. Nejde o porovnání šance na výhru.</p>'
    )

def build_html_report(
    candidates: list[CombinationCandidate],
    stats: RunStats,
    context: HistoricalContext,
    *,
    preset_key: str,
    preset_label: str,
    config: AppConfig,
) -> str:
    """Vrátí HTML report jako text bez zápisu na disk."""
    diagnostics = stats.diversity_diagnostics
    max_output_count = config.diversity.max_output_count
    validation = context.validation_summary()

    template = Template(_resource_text(_TEMPLATE_PATH))
    return template.safe_substitute({
        "css": _resource_text(_CSS_PATH),
        "preset_label": html.escape(preset_label),
        "preset_key": html.escape(preset_key),
        "generation_mode": html.escape(stats.generation_mode),
        "status_panel": _status_panel(stats, config, preset_label),
        "generated": format_int(stats.generated),
        "passed_min_score": format_int(stats.passed_min_score),
        "final_selected": format_int(stats.final_selected),
        "max_output_count": format_int(max_output_count),
        "stop_reason": html.escape(diagnostics.stop_reason),
        "total_possible": format_int(stats.total_possible),
        "passed_hard_filters": format_int(stats.passed_hard_filters),
        "kept_for_diversity": format_int(stats.kept_for_diversity),
        "funnel_svg": _funnel_svg(stats),
        "bottlenecks_html": _bottlenecks_html(stats),
        "recommendation_html": _recommendation_html(stats, config),
        "preset_comparison_html": _preset_comparison_html(preset_key),
        "filter_throughput_rows": _filter_throughput_html(stats),
        "strictness_rows": _strictness_html(stats),
        "number_frequency_svg": _number_frequency_svg(candidates, config),
        "diversity_considered": format_int(diagnostics.candidates_considered),
        "diversity_rejected_overlap": format_int(diagnostics.rejected_overlap),
        "diversity_rejected_pair": format_int(diagnostics.rejected_pair_reuse),
        "diversity_rejected_triplet": format_int(diagnostics.rejected_triplet_reuse),
        "selection_strategy": html.escape(diagnostics.selection_strategy.upper()),
        "mmr_candidate_evaluations": format_int(diagnostics.mmr_candidate_evaluations),
        "mmr_heap_recomputations": format_int(diagnostics.mmr_heap_recomputations),
        "mmr_average_gain": f"{diagnostics.mmr_average_gain:.4f}" if diagnostics.mmr_average_gain is not None else "-",
        "mmr_min_gain": f"{diagnostics.mmr_min_gain:.4f}" if diagnostics.mmr_min_gain is not None else "-",
        "mmr_max_gain": f"{diagnostics.mmr_max_gain:.4f}" if diagnostics.mmr_max_gain is not None else "-",
        "benchmark_total": f"{stats.benchmark.total_seconds:.3f}",
        "benchmark_generation": f"{stats.benchmark.generation_filter_scoring_seconds:.3f}",
        "benchmark_selection": f"{stats.benchmark.selection_seconds:.3f}",
        "benchmark_export": f"{stats.benchmark.export_seconds:.3f}",
        "benchmark_cps": f"{stats.benchmark.combinations_per_second:.1f}",
        "validation_json": html.escape(json.dumps(validation, ensure_ascii=False, indent=2)),
        "first_candidate_html": _first_candidate_html(candidates, config),
        "candidate_rows": _candidate_rows(candidates, config),
    })


def export_html_report(
    candidates: list[CombinationCandidate],
    stats: RunStats,
    context: HistoricalContext,
    path: str | Path,
    *,
    preset_key: str,
    preset_label: str,
    config: AppConfig,
) -> None:
    """Vytvoří přehledný HTML report po běhu."""
    output_path = ensure_parent(path)
    output_path.write_text(
        build_html_report(
            candidates,
            stats,
            context,
            preset_key=preset_key,
            preset_label=preset_label,
            config=config,
        ),
        encoding="utf-8",
    )
