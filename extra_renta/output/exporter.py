"""Veřejná fasáda pro exportní funkce Extra Renta.

Konkrétní implementace jsou rozdělené do menších modulů, aby se HTML, CSV,
JSON a serializace daly upravovat odděleně. Tento modul zachovává původní
importní cesty pro zbytek aplikace i pro starší skripty.
"""

from __future__ import annotations

from .csv_exporter import candidate_csv_rows, candidates_to_csv_text, export_candidates_to_csv
from .html_report import build_html_report, export_html_report
from .json_exporter import (
    candidates_json_payload,
    candidates_to_json_text,
    export_candidates_to_json,
    export_last_run_config,
    export_run_stats_to_json,
    last_run_config_to_json_text,
    load_last_run_config,
    run_stats_json_payload,
    run_stats_to_json_text,
)
from .serialization import (
    FILTER_EXPORT_LABELS,
    HARD_FILTER_EXPORT_ORDER,
)

__all__ = [
    "run_stats_to_json_text",
    "run_stats_json_payload",
    "last_run_config_to_json_text",
    "candidates_to_json_text",
    "candidates_json_payload",
    "build_html_report",
    "candidates_to_csv_text",
    "candidate_csv_rows",
    "FILTER_EXPORT_LABELS",
    "HARD_FILTER_EXPORT_ORDER",
    "export_candidates_to_csv",
    "export_candidates_to_json",
    "export_html_report",
    "export_last_run_config",
    "export_run_stats_to_json",
    "load_last_run_config",
]
