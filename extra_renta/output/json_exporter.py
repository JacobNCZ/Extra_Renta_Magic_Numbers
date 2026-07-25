"""JSON exporty kandidátů, statistik a posledního nastavení."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.models import AppConfig, CombinationCandidate, HistoricalContext, RunStats
from .serialization import HARD_FILTER_EXPORT_ORDER, candidate_to_dict, config_to_dict, ensure_parent


def candidates_json_payload(
    candidates: list[CombinationCandidate],
    config: AppConfig | None = None,
) -> dict[str, Any]:
    """Vrátí JSON serializovatelný payload finálních kandidátů."""
    return {
        "disclaimer": "Kandidáti jsou pouze výstupem filtrů, scoringu a diverzifikace. Nejde o predikci výhry.",
        "count": len(candidates),
        "candidates": [
            candidate_to_dict(candidate, rank, config)
            for rank, candidate in enumerate(candidates, start=1)
        ],
    }


def candidates_to_json_text(
    candidates: list[CombinationCandidate],
    config: AppConfig | None = None,
) -> str:
    """Vrátí JSON export kandidátů jako text bez zápisu na disk."""
    return json.dumps(candidates_json_payload(candidates, config), ensure_ascii=False, indent=2)


def export_candidates_to_json(
    candidates: list[CombinationCandidate],
    path: str | Path,
    config: AppConfig | None = None,
) -> None:
    """Uloží finální kandidáty do strukturovaného JSON exportu."""
    output_path = ensure_parent(path)
    output_path.write_text(candidates_to_json_text(candidates, config), encoding="utf-8")


def run_stats_json_payload(
    stats: RunStats,
    *,
    preset_key: str,
    preset_label: str,
    config: AppConfig,
    historical_context: HistoricalContext | None = None,
) -> dict[str, Any]:
    """Vrátí JSON serializovatelný payload statistik běhu."""
    payload: dict[str, Any] = {
        "disclaimer": "Statistiky ukazují zúžení prostoru kombinací. Nejde o důkaz vyšší pravděpodobnosti výhry.",
        "preset": {
            "key": preset_key,
            "label": preset_label,
        },
        "stats": stats.to_dict(),
        "filter_throughput": stats.filter_throughput(HARD_FILTER_EXPORT_ORDER),
        "config_snapshot": config_to_dict(config),
    }
    if historical_context is not None:
        payload["historical_validation"] = historical_context.validation_summary()
    return payload


def run_stats_to_json_text(
    stats: RunStats,
    *,
    preset_key: str,
    preset_label: str,
    config: AppConfig,
    historical_context: HistoricalContext | None = None,
) -> str:
    """Vrátí JSON export statistik jako text bez zápisu na disk."""
    payload = run_stats_json_payload(
        stats,
        preset_key=preset_key,
        preset_label=preset_label,
        config=config,
        historical_context=historical_context,
    )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_run_stats_to_json(
    stats: RunStats,
    path: str | Path,
    *,
    preset_key: str,
    preset_label: str,
    config: AppConfig,
    historical_context: HistoricalContext | None = None,
) -> None:
    """Uloží statistiku běhu včetně diagnostiky a použité konfigurace."""
    output_path = ensure_parent(path)
    output_path.write_text(
        run_stats_to_json_text(
            stats,
            preset_key=preset_key,
            preset_label=preset_label,
            config=config,
            historical_context=historical_context,
        ),
        encoding="utf-8",
    )


def last_run_config_to_json_text(payload: dict[str, Any]) -> str:
    """Vrátí poslední konfiguraci běhu jako JSON text."""
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_last_run_config(path: str | Path, payload: dict[str, Any]) -> None:
    """Uloží poslední interaktivně zvolené nastavení běhu."""
    output_path = ensure_parent(path)
    output_path.write_text(last_run_config_to_json_text(payload), encoding="utf-8")


def load_last_run_config(path: str | Path) -> dict[str, Any] | None:
    """Načte poslední nastavení, pokud existuje a je validní JSON."""
    input_path = Path(path)
    if not input_path.exists():
        return None
    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
