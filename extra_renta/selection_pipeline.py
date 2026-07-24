"""Finální MMR výběr kandidátů z připraveného kandidátního poolu."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from .core.mmr_selector import select_candidates_with_mmr
from .core.models import AppConfig, CombinationCandidate, DiversitySelectionResult

LOGGER = logging.getLogger(__name__)
SelectionProgressCallback = Callable[[int, int], None]
MMR_SELECTION = "mmr"


@dataclass(frozen=True)
class FinalSelectionResult:
    """Výsledek finálního výběru včetně času výběru."""

    selection: DiversitySelectionResult
    duration_seconds: float


def select_final_candidates(
    candidates: list[CombinationCandidate],
    config: AppConfig,
    *,
    progress_callback: SelectionProgressCallback | None = None,
    log_output: bool = True,
) -> FinalSelectionResult:
    """Vybere finální portfolio deterministickou MMR strategií."""
    start = time.perf_counter()
    if log_output:
        LOGGER.info("Start MMR / marginal-gain greedy finálního výběru...")
    selection = select_candidates_with_mmr(
        candidates,
        config,
        progress_callback=progress_callback,
    )
    return FinalSelectionResult(selection=selection, duration_seconds=time.perf_counter() - start)
