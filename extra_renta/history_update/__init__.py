"""Aktualizace historických tahů Extra Renty."""

from .fetcher import OFFICIAL_EXTRA_RENTA_RESULTS_URL, HistoryFetchError, fetch_official_draws
from .models import FetchedDraw, HistoryUpdateApplyResult, HistoryUpdatePreview
from .service import (
    apply_history_update,
    build_history_update_preview,
    check_new_draws_against_run,
    fetch_history_update_preview,
)

__all__ = [
    "OFFICIAL_EXTRA_RENTA_RESULTS_URL",
    "FetchedDraw",
    "HistoryFetchError",
    "HistoryUpdateApplyResult",
    "HistoryUpdatePreview",
    "apply_history_update",
    "build_history_update_preview",
    "check_new_draws_against_run",
    "fetch_history_update_preview",
    "fetch_official_draws",
]
