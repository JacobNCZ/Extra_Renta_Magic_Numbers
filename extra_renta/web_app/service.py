"""Servisní vrstva mezi Streamlit UI a Extra Renta pipeline.

Webová aplikace používá kompletní průchod a deterministický MMR výběr.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from extra_renta.core.models import CombinationCandidate, RunStats
from extra_renta.output.exporter import (
    FILTER_EXPORT_LABELS,
    HARD_FILTER_EXPORT_ORDER,
    build_html_report,
    candidates_to_csv_text,
    candidates_to_json_text,
    run_stats_to_json_text,
)
from extra_renta.output.serialization import config_to_dict
from extra_renta.pipeline import FULL_MODE, OUTPUT_MODE_SILENT, PipelineResult, run
from extra_renta.presets import PRESETS, PresetConfig, get_preset, preset_comparison_rows
from extra_renta.web_app.explanations import FIXED_RUN_TITLE

WEB_GENERATION_MODE = FULL_MODE
WEB_MIN_OUTPUT_COUNT = 1
WEB_MAX_OUTPUT_COUNT = 1_000
FIXED_RUN_HELP = (
    "Web projde všechny kombinace, aplikuje filtry a scoring a poté sestaví "
    "finální portfolio deterministickou MMR metodou."
)

ProgressCallback = Callable[[int, int, RunStats], None]
SelectionProgressCallback = Callable[[int, int], None]

SCORE_COMPONENT_LABELS: dict[str, str] = {
    "sum_balance": "Vyváženost součtu",
    "odd_even_balance": "Poměr sudých a lichých",
    "low_high_balance": "Poměr nízkých a vysokých",
    "tier_balance": "Rozložení do pásem",
    "bucket_balance": "Rozložení do skupin",
    "span_balance": "Rozpětí kombinace",
    "gap_balance": "Vyváženost mezer",
    "historical_similarity": "Historická podobnost",
    "pattern_safety": "Omezení jednoduchých vzorů",
    "overall_uniformity": "Celková vyváženost",
}


@dataclass(frozen=True)
class WebRunOptions:
    """Validované volby z webového formuláře."""

    preset_key: str
    max_output_count: int | None = None
    export_outputs: bool = False


@dataclass(frozen=True)
class ExportBundle:
    csv_text: str
    candidates_json: str
    config_json: str
    stats_json: str
    html_report: str
    zip_archive: bytes


def available_presets() -> tuple[PresetConfig, ...]:
    return tuple(PRESETS.values())


def preset_options() -> dict[str, str]:
    return {preset.key: preset.label for preset in available_presets()}


def preset_detail_rows(preset: PresetConfig) -> list[dict[str, object]]:
    cfg = preset.config
    return [
        {"Pravidlo": "Součet", "Hodnota": f"{cfg.filters.sum_min}–{cfg.filters.sum_max}"},
        {"Pravidlo": "Sudá / lichá", "Hodnota": str(cfg.filters.allowed_odd_counts)},
        {"Pravidlo": "Nízká čísla", "Hodnota": str(cfg.filters.allowed_low_counts)},
        {"Pravidlo": "Historický překryv", "Hodnota": f"max {cfg.filters.max_historical_overlap} čísel"},
        {"Pravidlo": "Minimální skóre", "Hodnota": str(cfg.scoring.min_score_to_keep)},
        {"Pravidlo": "Max. kandidátů pro MMR", "Hodnota": f"{cfg.scoring.max_candidates_for_diversity:,}".replace(",", " ")},
        {"Pravidlo": "Maximální limit výstupu", "Hodnota": str(cfg.diversity.max_output_count)},
        {"Pravidlo": "Překryv mezi finálními", "Hodnota": str(cfg.diversity.max_overlap_between_selected)},
        {"Pravidlo": "Finální výběr", "Hodnota": "MMR / marginal-gain greedy"},
    ]


def preset_comparison_table_rows() -> list[dict[str, str]]:
    return list(preset_comparison_rows())


def validate_web_options(options: WebRunOptions) -> None:
    if options.preset_key not in PRESETS:
        raise ValueError(f"Neznámá předvolba: {options.preset_key}")
    if options.max_output_count is not None and not (
        WEB_MIN_OUTPUT_COUNT <= options.max_output_count <= WEB_MAX_OUTPUT_COUNT
    ):
        raise ValueError(
            f"Maximální limit výstupu musí být mezi {WEB_MIN_OUTPUT_COUNT} a {WEB_MAX_OUTPUT_COUNT}."
        )


def normalize_web_options(options: WebRunOptions) -> WebRunOptions:
    validate_web_options(options)
    preset = get_preset(options.preset_key)
    maximum = options.max_output_count
    if maximum is None:
        maximum = preset.config.diversity.max_output_count
    normalized = WebRunOptions(
        preset_key=options.preset_key,
        max_output_count=int(maximum),
        export_outputs=options.export_outputs,
    )
    validate_web_options(normalized)
    return normalized


def _web_preset_from_options(options: WebRunOptions) -> PresetConfig:
    normalized = normalize_web_options(options)
    preset = get_preset(normalized.preset_key)
    diversity = replace(
        preset.config.diversity,
        max_output_count=normalized.max_output_count or preset.config.diversity.max_output_count,
    )
    return replace(preset, config=replace(preset.config, diversity=diversity))


def run_web_generation(
    options: WebRunOptions,
    *,
    progress_callback: ProgressCallback | None = None,
    selection_progress_callback: SelectionProgressCallback | None = None,
) -> PipelineResult:
    normalized = normalize_web_options(options)
    preset = _web_preset_from_options(normalized)
    return run(
        preset,
        generation_mode=WEB_GENERATION_MODE,
        export_outputs=normalized.export_outputs,
        output_mode=OUTPUT_MODE_SILENT,
        progress_callback=progress_callback,
        selection_progress_callback=selection_progress_callback,
    )


def result_summary(result: PipelineResult) -> dict[str, object]:
    stats = result.stats
    diagnostics = stats.diversity_diagnostics
    return {
        "Předvolba": result.preset_label,
        "Typ běhu": FIXED_RUN_TITLE,
        "Celkem možných": stats.total_possible,
        "Vygenerováno": stats.generated,
        "Po tvrdých filtrech": stats.passed_hard_filters,
        "Po minimálním skóre": stats.passed_min_score,
        "Ponecháno pro MMR": stats.kept_for_diversity,
        "Limit kandidátního poolu": get_preset(result.preset_key).config.scoring.max_candidates_for_diversity,
        "Finálně vybráno": stats.final_selected,
        "Maximální limit výstupu": diagnostics.max_output_count,
        "Důvod ukončení": diagnostics.stop_reason,
        "MMR přepočty": diagnostics.mmr_heap_recomputations,
        "Čas celkem [s]": round(stats.benchmark.total_seconds, 3),
    }


def _short_score_note(candidate: CombinationCandidate) -> str:
    if candidate.score.notes:
        return "; ".join(candidate.score.notes[:2])
    return "Prošlo tvrdými filtry a minimálním skóre."


def candidate_to_table_row(candidate: CombinationCandidate, rank: int) -> dict[str, object]:
    """Převede kandidáta na zjednodušený řádek výsledkové tabulky."""
    metrics = candidate.metrics
    return {
        "Pořadí": rank,
        "Kombinace": " ".join(str(number) for number in candidate.numbers),
        "Skóre": round(candidate.score.total_score, 2),
        "Součet": metrics.total_sum,
        "Sudá / lichá": f"{metrics.even_count} / {metrics.odd_count}",
        "Nízká / vysoká": f"{metrics.low_count} / {metrics.high_count}",
        "Krátké vysvětlení": _short_score_note(candidate),
    }


def candidate_selection_reason(candidate: CombinationCandidate) -> str:
    """Vrátí lidské shrnutí individuálního skóre i MMR přínosu."""
    metrics = candidate.metrics
    reasons = [
        "prošla všemi tvrdými filtry",
        f"dosáhla individuálního skóre {candidate.score.total_score:.2f}",
        f"má součet {metrics.total_sum}",
        f"poměr sudá/lichá {metrics.even_count}/{metrics.odd_count}",
    ]
    if candidate.selection is not None:
        reasons.extend((
            f"MMR marginální přínos {candidate.selection.marginal_gain:.4f}",
            f"přidala {candidate.selection.new_pairs} dosud nepoužitých párů",
        ))
    return "Kombinace byla vybrána, protože " + ", ".join(reasons) + "."

def candidate_to_technical_table_row(candidate: CombinationCandidate, rank: int) -> dict[str, object]:
    """Převede kandidáta na rozšířený řádek včetně MMR diagnostiky."""
    row = candidate_to_table_row(candidate, rank)
    metrics = candidate.metrics
    row.update({
        "Rozpětí": metrics.span,
        "Historický překryv": metrics.max_historical_overlap,
        "Sousední dvojice": metrics.adjacent_pairs,
        "Nejdelší sekvence": metrics.max_consecutive_run_length,
        "Max. stejná koncovka": metrics.max_same_last_digit,
        "Opakování z posledního tahu": metrics.repeated_from_last_draw,
        "Sousedi posledního tahu": metrics.neighbors_of_last_draw,
        "Pásma": str(metrics.tier_counts),
        "Buckety": str(metrics.bucket_counts),
    })
    if candidate.selection is not None:
        row.update({
            "MMR přínos": round(candidate.selection.marginal_gain, 4),
            "Nové páry": candidate.selection.new_pairs,
            "Vyváženost čísel": round(candidate.selection.number_balance, 4),
            "Pokrytí párů": round(candidate.selection.pair_coverage, 4),
        })
    return row

def candidate_detail_row(candidate: CombinationCandidate) -> dict[str, object]:
    """Vrátí detailní metriky kandidáta a jeho MMR přínos."""
    metrics = candidate.metrics
    row: dict[str, object] = {
        "Čísla": " ".join(str(number) for number in candidate.numbers),
        "Skóre": round(candidate.score.total_score, 2),
        "Součet": metrics.total_sum,
        "Sudá": metrics.even_count,
        "Lichá": metrics.odd_count,
        "Nízká": metrics.low_count,
        "Vysoká": metrics.high_count,
        "Pásma": str(metrics.tier_counts),
        "Buckety": str(metrics.bucket_counts),
        "Rozpětí": metrics.span,
        "Mezery": str(metrics.gaps),
        "Max. mezera": metrics.max_gap,
        "Směr. odchylka mezer": round(metrics.gap_std, 3),
        "Sousední dvojice": metrics.adjacent_pairs,
        "Nejdelší sekvence": metrics.max_consecutive_run_length,
        "Max. stejná koncovka": metrics.max_same_last_digit,
        "Historický překryv": metrics.max_historical_overlap,
        "Opakování z posledního tahu": metrics.repeated_from_last_draw,
        "Sousedi posledního tahu": metrics.neighbors_of_last_draw,
    }
    if candidate.selection is not None:
        row.update({
            "MMR marginální přínos": round(candidate.selection.marginal_gain, 5),
            "MMR normalizované skóre": round(candidate.selection.normalized_score, 5),
            "MMR vyváženost čísel": round(candidate.selection.number_balance, 5),
            "MMR pokrytí párů": round(candidate.selection.pair_coverage, 5),
            "MMR diverzita překryvu": round(candidate.selection.overlap_diversity, 5),
            "MMR bezpečnost opakování": round(candidate.selection.pair_reuse_safety, 5),
            "Nové páry": candidate.selection.new_pairs,
        })
    return row

def candidates_table_rows(result: PipelineResult) -> list[dict[str, object]]:
    """Vrátí tabulkové řádky finálních kandidátů."""
    return [candidate_to_table_row(candidate, rank) for rank, candidate in enumerate(result.selected, start=1)]


def candidates_technical_table_rows(result: PipelineResult) -> list[dict[str, object]]:
    """Vrátí rozšířené tabulkové řádky finálních kandidátů pro pokročilý režim."""
    return [
        candidate_to_technical_table_row(candidate, rank)
        for rank, candidate in enumerate(result.selected, start=1)
    ]


def score_breakdown_rows(candidate: CombinationCandidate) -> list[dict[str, object]]:
    """Vrátí rozpad skóre pro detail kombinace."""
    return [
        {
            "Komponenta": SCORE_COMPONENT_LABELS.get(key, key),
            "Body": round(float(value), 3),
        }
        for key, value in sorted(candidate.score.components.items())
    ]


def filter_throughput_rows(stats: RunStats) -> list[dict[str, object]]:
    """Vrátí propustnost tvrdých filtrů s českými názvy."""
    rows: list[dict[str, object]] = []
    for row in stats.filter_throughput(HARD_FILTER_EXPORT_ORDER):
        name = str(row["filter"])
        rows.append({
            "Filtr": FILTER_EXPORT_LABELS.get(name, name),
            "Zamítnuto": int(row["rejected"]),
            "Zůstává": int(row["passed_after_filter"]),
            "% ze zpracovaných": round(float(row["passed_after_filter_pct_of_generated"]), 4),
        })
    return rows


def pipeline_funnel_rows(stats: RunStats) -> list[dict[str, object]]:
    """Vrátí hodnoty průchodu pipeline pro graf i tabulku."""
    phases = [
        ("Vygenerováno", stats.generated),
        ("Po tvrdých filtrech", stats.passed_hard_filters),
        ("Po minimálním skóre", stats.passed_min_score),
        ("Kandidátní pool", stats.kept_for_diversity),
        ("Finální výběr", stats.final_selected),
    ]
    return [
        {
            "Fáze": phase,
            "Počet": count,
            "% z vygenerovaných": round(stats.percent_of_generated(count), 4),
            "% z celkového prostoru": round(stats.percent_of_total(count), 6),
        }
        for phase, count in phases
    ]


def number_frequency_rows(result: PipelineResult) -> list[dict[str, int]]:
    """Vrátí četnost jednotlivých čísel ve finálním výběru."""
    cfg = get_preset(result.preset_key).config
    counts = {number: 0 for number in range(cfg.generator.number_min, cfg.generator.number_max + 1)}
    for candidate in result.selected:
        for number in candidate.numbers:
            counts[number] += 1
    return [{"Číslo": number, "Četnost": count} for number, count in counts.items()]


def number_frequency_grid_rows(result: PipelineResult) -> list[dict[str, object]]:
    """Vrátí přehled čísel 1–33 jako čitelnou mřížku po řádcích."""
    frequencies = {row["Číslo"]: row["Četnost"] for row in number_frequency_rows(result)}
    rows: list[dict[str, object]] = []
    for start in (1, 12, 23):
        end = min(start + 10, 33)
        rows.append({
            "Rozsah": f"{start}–{end}",
            **{str(number): frequencies.get(number, 0) for number in range(start, end + 1)},
        })
    return rows


def _histogram_rows(values: list[float], *, bin_size: int, label: str) -> list[dict[str, object]]:
    if not values:
        return []
    min_value = int(min(values) // bin_size * bin_size)
    max_value = int(max(values) // bin_size * bin_size)
    buckets = {start: 0 for start in range(min_value, max_value + bin_size, bin_size)}
    for value in values:
        start = int(value // bin_size * bin_size)
        buckets[start] = buckets.get(start, 0) + 1
    return [
        {label: f"{start}–{start + bin_size - 1}", "Počet": count}
        for start, count in sorted(buckets.items())
    ]


def score_histogram_rows(result: PipelineResult) -> list[dict[str, object]]:
    """Vrátí histogram skóre finálních kandidátů."""
    return _histogram_rows([candidate.score.total_score for candidate in result.selected], bin_size=5, label="Skóre")


def candidate_pool_score_histogram_rows(result: PipelineResult) -> list[dict[str, object]]:
    """Vrátí histogram skóre kandidátního poolu, ze kterého vybírá MMR."""
    if not result.candidate_pool:
        return []
    return _histogram_rows([candidate.score.total_score for candidate in result.candidate_pool], bin_size=5, label="Skóre")


def sum_histogram_rows(result: PipelineResult) -> list[dict[str, object]]:
    """Vrátí histogram součtů finálních kombinací."""
    return _histogram_rows([candidate.metrics.total_sum for candidate in result.selected], bin_size=5, label="Součet")


def sensitivity_hint_rows(result: PipelineResult) -> list[dict[str, object]]:
    """Vrátí orientační diagnostiku prvních důvodů zamítnutí."""
    rows = sorted(result.stats.failed_by_filter.items(), key=lambda item: item[1], reverse=True)
    output: list[dict[str, object]] = []
    for name, count in rows[:8]:
        label = FILTER_EXPORT_LABELS.get(name, name)
        output.append({
            "Pravidlo / filtr": label,
            "Zamítnuto": count,
            "Komentář": "První zaznamenaný důvod zamítnutí; nejde o plnou ablaci pravidla.",
        })
    diagnostics = result.stats.diversity_diagnostics
    if diagnostics.rejected_total:
        output.append({
            "Pravidlo / filtr": "Finální MMR / tvrdé portfolio limity",
            "Zamítnuto": diagnostics.rejected_total,
            "Komentář": f"Důvod ukončení: {diagnostics.stop_reason}.",
        })
    if not output:
        output.append({"Pravidlo / filtr": "-", "Zamítnuto": 0, "Komentář": "Filtry v tomto běhu nezamítly žádnou kombinaci."})
    return output

def options_signature(options: WebRunOptions) -> dict[str, Any]:
    """Vrátí stabilní snapshot voleb pro detekci zastaralého výsledku."""
    normalized = normalize_web_options(options)
    return {
        "preset_key": normalized.preset_key,
        "max_output_count": normalized.max_output_count,
        "run_type": FIXED_RUN_TITLE,
    }



def candidate_pool_number_snapshot(result: PipelineResult) -> frozenset[tuple[int, ...]]:
    """Vrátí kompaktní množinu čísel kandidátního poolu pro pozdější porovnání."""
    return frozenset(candidate.numbers for candidate in (result.candidate_pool or []))


def candidate_pool_score_cutoff(result: PipelineResult) -> float | None:
    """Vrátí nejnižší skóre uloženého kandidátního poolu."""
    candidates = result.candidate_pool or []
    return min((candidate.score.total_score for candidate in candidates), default=None)

def strip_candidate_pool(result: PipelineResult) -> PipelineResult:
    """Vrátí výsledek bez velkého kandidátního poolu pro úsporné uložení v session_state."""
    return replace(result, candidate_pool=None)


def run_recommendation(result: PipelineResult) -> tuple[str, str]:
    """Vrátí stav a doporučený další krok bez povinného cíle."""
    stats = result.stats
    maximum = stats.diversity_diagnostics.max_output_count
    if stats.final_selected == 0:
        return ("warning", "Nebyla vybrána žádná kombinace. Zvaž mírnější předvolbu nebo filtry.")
    if stats.final_selected >= maximum:
        return ("success", "Byl dosažen maximální limit výstupu. Výsledek je připraven ke kontrole a exportu.")
    return (
        "success",
        "Výběr skončil před maximálním limitem, což je platný výsledek. Důvod: " + stats.diversity_diagnostics.stop_reason + ".",
    )

def web_config_payload(options: WebRunOptions) -> dict[str, Any]:
    """Vrátí nastavení běhu jako JSON serializovatelný slovník."""
    normalized = normalize_web_options(options)
    preset = _web_preset_from_options(normalized)
    return {
        "preset_key": normalized.preset_key,
        "preset_label": preset.label,
        "run_type": FIXED_RUN_TITLE,
        "generation_mode_internal": WEB_GENERATION_MODE,
        "selection_strategy": "mmr",
        "note": "Kompletní průchod všemi kombinacemi; finální portfolio vybírá deterministické MMR.",
        "max_output_count": normalized.max_output_count,
        "candidate_pool_limit": preset.config.scoring.max_candidates_for_diversity,
        "export_outputs": normalized.export_outputs,
        "config_snapshot": config_to_dict(preset.config),
    }

def _build_export_zip(
    *,
    csv_text: str,
    candidates_json: str,
    config_json: str,
    stats_json: str,
    html_report: str,
) -> bytes:
    """Sestaví kompletní exportní balíček v paměti."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("extra_renta_candidates.csv", csv_text)
        archive.writestr("extra_renta_candidates.json", candidates_json)
        archive.writestr("extra_renta_config.json", config_json)
        archive.writestr("extra_renta_stats.json", stats_json)
        archive.writestr("extra_renta_report.html", html_report)
    return buffer.getvalue()


def build_export_bundle(result: PipelineResult, options: WebRunOptions) -> ExportBundle:
    """Připraví všechny webové exporty v paměti bez zápisu na disk."""
    preset = _web_preset_from_options(options)
    csv_text = candidates_to_csv_text(result.selected)
    candidates_json = candidates_to_json_text(result.selected, preset.config)
    config_json = json.dumps(web_config_payload(options), ensure_ascii=False, indent=2)
    stats_json = run_stats_to_json_text(
        result.stats,
        preset_key=result.preset_key,
        preset_label=result.preset_label,
        config=preset.config,
        historical_context=result.historical_context,
    )
    html_report = build_html_report(
        result.selected,
        result.stats,
        result.historical_context,
        preset_key=result.preset_key,
        preset_label=result.preset_label,
        config=preset.config,
    )
    return ExportBundle(
        csv_text=csv_text,
        candidates_json=candidates_json,
        config_json=config_json,
        stats_json=stats_json,
        html_report=html_report,
        zip_archive=_build_export_zip(
            csv_text=csv_text,
            candidates_json=candidates_json,
            config_json=config_json,
            stats_json=stats_json,
            html_report=html_report,
        ),
    )
