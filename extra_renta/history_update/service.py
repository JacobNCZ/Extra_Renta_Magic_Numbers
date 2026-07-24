"""Služby pro kontrolu a aktualizaci historických tahů."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from ..combination_check import CombinationCheckResult, check_custom_combination
from ..core.models import AppConfig, CombinationCandidate, HistoricalContext, NumberTuple
from ..data import historical_draws as historical_draws_module
from ..data.historical_draws import HISTORICAL_DRAWS
from .fetcher import (
    OFFICIAL_EXTRA_RENTA_RESULTS_URL,
    HistoryFetchError,
    fetch_available_history_draws,
    fetch_available_history_result,
    fetch_draws_from_url,
)
from .models import FetchedDraw, HistoryUpdateApplyResult, HistoryUpdatePreview

DrawFetcher = Callable[[], tuple[FetchedDraw, ...]]


def _to_number_tuple(numbers: Iterable[object]) -> NumberTuple:
    return tuple(sorted(int(number) for number in numbers))


def current_history_index(raw_draws: list[dict] | None = None) -> dict[str, NumberTuple]:
    """Vrátí index lokální historie podle data."""
    rows = HISTORICAL_DRAWS if raw_draws is None else raw_draws
    index: dict[str, NumberTuple] = {}
    for row in rows:
        date = str(row.get("date", ""))
        try:
            numbers = _to_number_tuple(row.get("numbers", []))
        except (TypeError, ValueError):
            continue
        if date:
            index[date] = numbers
    return index


def build_history_update_preview(
    fetched_draws: Iterable[FetchedDraw],
    *,
    current_draws: list[dict] | None = None,
    source_url: str = OFFICIAL_EXTRA_RENTA_RESULTS_URL,
    source_error: str | None = None,
    source_errors: tuple[str, ...] = (),
) -> HistoryUpdatePreview:
    """Porovná stažené tahy s lokální historií."""
    fetched = tuple(sorted(fetched_draws, key=lambda draw: draw.date))
    current = current_history_index(current_draws)
    new_draws: list[FetchedDraw] = []
    existing_draws: list[FetchedDraw] = []
    conflicting_draws: list[FetchedDraw] = []
    invalid_draws: list[FetchedDraw] = []

    for draw in fetched:
        if len(draw.numbers) != 7 or len(set(draw.numbers)) != 7 or any(number < 1 or number > 33 for number in draw.numbers):
            invalid_draws.append(draw)
            continue
        existing_numbers = current.get(draw.date)
        if existing_numbers is None:
            new_draws.append(draw)
        elif existing_numbers == draw.numbers:
            existing_draws.append(draw)
        else:
            conflicting_draws.append(draw)

    return HistoryUpdatePreview(
        fetched_draws=fetched,
        new_draws=tuple(new_draws),
        existing_draws=tuple(existing_draws),
        conflicting_draws=tuple(conflicting_draws),
        invalid_draws=tuple(invalid_draws),
        source_url=source_url,
        source_error=source_error,
        source_errors=source_errors,
    )


def fetch_history_update_preview(
    *,
    fetcher: DrawFetcher | None = None,
    source_url: str = OFFICIAL_EXTRA_RENTA_RESULTS_URL,
) -> HistoryUpdatePreview:
    """Stáhne externí tahy a vrátí preview aktualizace."""
    actual_fetcher = fetcher
    try:
        if actual_fetcher is not None:
            fetched = actual_fetcher()
        elif source_url == OFFICIAL_EXTRA_RENTA_RESULTS_URL:
            # Běžně používáme diagnostický fetch_result. Podmínka níže zachovává
            # kompatibilitu se staršími testy nebo externím kódem, který monkeypatchuje
            # původní service.fetch_available_history_draws.
            if getattr(fetch_available_history_draws, "__module__", "") != "extra_renta.history_update.fetcher":
                fetched = fetch_available_history_draws()
                actual_source_url = fetched[0].source if fetched else source_url
                return build_history_update_preview(fetched, source_url=actual_source_url)
            fetch_result = fetch_available_history_result()
            fetched = fetch_result.draws
            actual_source_url = fetch_result.source_url
            source_errors = fetch_result.errors
            return build_history_update_preview(fetched, source_url=actual_source_url, source_errors=source_errors)
        else:
            fetched = fetch_draws_from_url(source_url)
    except HistoryFetchError as exc:
        return build_history_update_preview((), source_url=source_url, source_error=str(exc), source_errors=(str(exc),))

    actual_source_url = fetched[0].source if fetched else source_url
    return build_history_update_preview(fetched, source_url=actual_source_url)


def _numbers_to_raw_value(numbers: NumberTuple) -> str:
    return " ".join(str(number) for number in numbers)


def check_new_draws_against_run(
    new_draws: Iterable[FetchedDraw],
    *,
    config: AppConfig,
    historical_context: HistoricalContext,
    candidate_pool: list[CombinationCandidate],
    selected: list[CombinationCandidate],
) -> tuple[tuple[FetchedDraw, CombinationCheckResult], ...]:
    """Zkontroluje více nových tahů proti již vytvořenému kandidátnímu poolu."""
    results: list[tuple[FetchedDraw, CombinationCheckResult]] = []
    for draw in new_draws:
        check = check_custom_combination(
            _numbers_to_raw_value(draw.numbers),
            config=config,
            historical_context=historical_context,
            candidate_pool=candidate_pool,
            selected=selected,
        )
        results.append((draw, check))
    return tuple(results)


def historical_draws_py_path() -> Path:
    """Vrátí cestu k lokálnímu Python souboru s historickými tahy."""
    module_file = getattr(historical_draws_module, "__file__", None)
    if not module_file:
        raise RuntimeError("Nelze zjistit cestu k extra_renta.data.historical_draws.")
    return Path(module_file)


def format_historical_draws_py(rows: list[dict]) -> str:
    """Vytvoří čitelný obsah ``historical_draws.py``."""
    lines = [
        '"""Historické tahy Extra Renty používané jako lokální datový zdroj."""',
        "",
        "# Soubor může být aktualizován nástrojem pro aktualizaci historie.",
        "# Historická data slouží pouze pro filtrování/reporting, ne pro predikci výhry.",
        "",
        "HISTORICAL_DRAWS = [",
    ]
    for row in sorted(rows, key=lambda item: str(item.get("date", ""))):
        date = str(row["date"])
        numbers = [int(number) for number in row["numbers"]]
        lines.append(f'    {{"date": "{date}", "numbers": {numbers}}},')
    lines.append("]")
    lines.append("")
    return "\n".join(lines)


def merge_history_rows(new_draws: Iterable[FetchedDraw], *, current_draws: list[dict] | None = None) -> list[dict]:
    """Sloučí nové tahy s lokální historií podle data."""
    rows = list(HISTORICAL_DRAWS if current_draws is None else current_draws)
    index = {str(row.get("date", "")): row for row in rows}
    for draw in new_draws:
        index[draw.date] = {"date": draw.date, "numbers": list(draw.numbers)}
    return sorted(index.values(), key=lambda item: str(item.get("date", "")))


def apply_history_update(
    preview: HistoryUpdatePreview,
    *,
    target_path: Path | None = None,
    create_backup: bool = True,
) -> HistoryUpdateApplyResult:
    """Zapíše nové tahy do lokálního ``historical_draws.py``."""
    if preview.source_error:
        return HistoryUpdateApplyResult(preview=preview, updated=False, message="Aktualizace se neprovedla: zdroj nebyl dostupný.")
    if not preview.new_draws:
        return HistoryUpdateApplyResult(preview=preview, updated=False, message="Nejsou dostupné žádné nové tahy k uložení.")
    if preview.conflicting_draws:
        return HistoryUpdateApplyResult(
            preview=preview,
            updated=False,
            message="Aktualizace se neprovedla: některá data jsou v konfliktu s lokální historií.",
        )

    path = target_path or historical_draws_py_path()
    backup_path: Path | None = None
    if create_backup and path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(f".backup_{timestamp}.py")
        shutil.copy2(path, backup_path)

    merged_rows = merge_history_rows(preview.new_draws)
    path.write_text(format_historical_draws_py(merged_rows), encoding="utf-8")
    return HistoryUpdateApplyResult(
        preview=preview,
        updated=True,
        backup_path=str(backup_path) if backup_path else None,
        target_path=str(path),
        message=f"Historická data byla aktualizována. Přidáno tahů: {len(preview.new_draws)}.",
    )
