"""Trvalá lokální historie kombinací na prvním místě z dokončených běhů."""

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from extra_renta.pipeline import PipelineResult
from extra_renta.web_app.service import WebRunOptions, result_summary, web_config_payload

_DB_ENV = "EXTRA_RENTA_HISTORY_DB"
_DEFAULT_DB = Path.home() / ".extra_renta" / "run_history.sqlite3"


def history_database_path() -> Path:
    """Vrátí konfigurovatelnou cestu lokální SQLite databáze."""
    configured = os.environ.get(_DB_ENV)
    return Path(configured).expanduser().resolve() if configured else _DEFAULT_DB


def _connect(path: str | Path | None = None) -> sqlite3.Connection:
    database_path = Path(path) if path is not None else history_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


@contextmanager
def _history_connection(path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """Otevře transakci a vždy korektně uzavře SQLite spojení."""
    connection = _connect(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_history_database(path: str | Path | None = None) -> Path:
    """Vytvoří databázi a tabulku, pokud ještě neexistují."""
    database_path = Path(path) if path is not None else history_database_path()
    with _history_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS first_place_runs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                preset_key TEXT NOT NULL,
                preset_label TEXT NOT NULL,
                numbers_json TEXT NOT NULL,
                total_score REAL NOT NULL,
                marginal_gain REAL,
                new_pairs INTEGER,
                selected_count INTEGER NOT NULL,
                max_output_count INTEGER NOT NULL,
                stop_reason TEXT NOT NULL,
                total_seconds REAL NOT NULL,
                candidate_json TEXT NOT NULL,
                config_json TEXT NOT NULL,
                summary_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_first_place_runs_created_at ON first_place_runs(created_at DESC)"
        )
    return database_path


def _candidate_payload(result: PipelineResult) -> dict[str, Any]:
    candidate = result.selected[0]
    selection = candidate.selection
    return {
        "numbers": list(candidate.numbers),
        "score": candidate.score.total_score,
        "score_components": dict(candidate.score.components),
        "score_notes": list(candidate.score.notes),
        "metrics": {
            "sum": candidate.metrics.total_sum,
            "odd_count": candidate.metrics.odd_count,
            "even_count": candidate.metrics.even_count,
            "low_count": candidate.metrics.low_count,
            "high_count": candidate.metrics.high_count,
            "span": candidate.metrics.span,
            "gaps": list(candidate.metrics.gaps),
            "historical_overlap": candidate.metrics.max_historical_overlap,
        },
        "selection": None
        if selection is None
        else {
            "marginal_gain": selection.marginal_gain,
            "normalized_score": selection.normalized_score,
            "number_balance": selection.number_balance,
            "pair_coverage": selection.pair_coverage,
            "overlap_diversity": selection.overlap_diversity,
            "pair_reuse_safety": selection.pair_reuse_safety,
            "new_pairs": selection.new_pairs,
        },
    }


def save_first_place_run(
    result: PipelineResult,
    options: WebRunOptions,
    *,
    path: str | Path | None = None,
) -> str | None:
    """Uloží první kombinaci a detaily běhu; prázdný výsledek neukládá."""
    if not result.selected:
        return None

    database_path = initialize_history_database(path)
    run_id = uuid.uuid4().hex
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    candidate = result.selected[0]
    selection = candidate.selection
    summary = result_summary(result)
    config_payload = web_config_payload(options)

    with _history_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO first_place_runs (
                id, created_at, preset_key, preset_label, numbers_json,
                total_score, marginal_gain, new_pairs, selected_count,
                max_output_count, stop_reason, total_seconds,
                candidate_json, config_json, summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                created_at,
                result.preset_key,
                result.preset_label,
                json.dumps(list(candidate.numbers), ensure_ascii=False),
                float(candidate.score.total_score),
                float(selection.marginal_gain) if selection is not None else None,
                int(selection.new_pairs) if selection is not None else None,
                int(result.stats.final_selected),
                int(result.stats.diversity_diagnostics.max_output_count),
                str(result.stats.diversity_diagnostics.stop_reason),
                float(result.stats.benchmark.total_seconds),
                json.dumps(_candidate_payload(result), ensure_ascii=False),
                json.dumps(config_payload, ensure_ascii=False),
                json.dumps(summary, ensure_ascii=False),
            ),
        )
    return run_id


def list_first_place_runs(*, limit: int = 250, path: str | Path | None = None) -> list[dict[str, Any]]:
    """Vrátí historii od nejnovějšího běhu."""
    database_path = initialize_history_database(path)
    with _history_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, created_at, preset_key, preset_label, numbers_json,
                   total_score, marginal_gain, new_pairs, selected_count,
                   max_output_count, stop_reason, total_seconds
            FROM first_place_runs
            ORDER BY created_at DESC, rowid DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()

    return [
        {
            "ID běhu": str(row["id"]),
            "Datum a čas": str(row["created_at"]),
            "Předvolba": str(row["preset_label"]),
            "První kombinace": " ".join(f"{number:02d}" for number in json.loads(row["numbers_json"])),
            "Skóre": round(float(row["total_score"]), 3),
            "MMR přínos": None if row["marginal_gain"] is None else round(float(row["marginal_gain"]), 5),
            "Nové páry": row["new_pairs"],
            "Vybráno": int(row["selected_count"]),
            "Max. limit": int(row["max_output_count"]),
            "Důvod ukončení": str(row["stop_reason"]),
            "Čas [s]": round(float(row["total_seconds"]), 3),
        }
        for row in rows
    ]


def get_first_place_run(record_id: str, *, path: str | Path | None = None) -> dict[str, Any] | None:
    """Vrátí kompletní detail jednoho uloženého běhu."""
    database_path = initialize_history_database(path)
    with _history_connection(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM first_place_runs WHERE id = ?",
            (record_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "preset_key": row["preset_key"],
        "preset_label": row["preset_label"],
        "candidate": json.loads(row["candidate_json"]),
        "config": json.loads(row["config_json"]),
        "summary": json.loads(row["summary_json"]),
    }


def delete_first_place_run(record_id: str, *, path: str | Path | None = None) -> bool:
    """Smaže jeden záznam podle ID."""
    database_path = initialize_history_database(path)
    with _history_connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM first_place_runs WHERE id = ?", (record_id,))
    return cursor.rowcount > 0


def clear_first_place_history(*, path: str | Path | None = None) -> int:
    """Smaže celou historii a vrátí počet odstraněných řádků."""
    database_path = initialize_history_database(path)
    with _history_connection(database_path) as connection:
        count = int(connection.execute("SELECT COUNT(*) FROM first_place_runs").fetchone()[0])
        connection.execute("DELETE FROM first_place_runs")
    return count


def first_place_history_csv(*, path: str | Path | None = None) -> str:
    """Vrátí historii jako CSV pro stažení."""
    rows = list_first_place_runs(limit=100_000, path=path)
    if not rows:
        return ""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
