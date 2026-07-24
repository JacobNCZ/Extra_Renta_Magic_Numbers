"""Tvorba kandidátního poolu pro Extra Renta pipeline.

Základní metriky se počítají právě jednou. Po strukturálních filtrech se do
stejného objektu doplní pouze historický překryv a spustí se jen historické
kontroly. Kandidátní pool kombinuje nejvyšší skóre s deterministickou rezervou,
aby finální MMR vidělo i různorodější kandidáty mimo čisté top-score pořadí.
"""

from __future__ import annotations

import heapq
import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from .core.combination_generator import generate_all_combinations, generate_random_combinations
from .core.filters import apply_historical_filters, apply_structural_filters, merge_filter_results
from .core.models import CombinationCandidate, HistoricalContext, NumberTuple, RunStats
from .core.scoring import score_combination
from .core.statistics import add_historical_overlap, calculate_combination_metrics
from .output.printer import format_progress_bar
from .presets import PresetConfig

LOGGER = logging.getLogger(__name__)

FULL_MODE = "full"
SAMPLE_MODE = "sample"

ProgressCallback = Callable[[int, int, RunStats], None]


@dataclass(frozen=True)
class CandidatePoolResult:
    """Výsledek fáze generování, filtrování a scoringu."""

    candidates: list[CombinationCandidate]
    duration_seconds: float


def combination_iterator(
    preset: PresetConfig,
    generation_mode: str,
    sample_size: int,
    seed: int | None,
) -> Iterator[NumberTuple]:
    """Vrátí kompletní nebo náhodně vzorkovaný iterátor kombinací."""
    config = preset.config
    if generation_mode == FULL_MODE:
        yield from generate_all_combinations(config.generator)
        return

    if generation_mode == SAMPLE_MODE:
        yield from generate_random_combinations(config.generator, sample_size, seed=seed)
        return

    raise ValueError(f"Neznámý režim generování: {generation_mode}")


def _score_heap_key(candidate: CombinationCandidate) -> tuple[float, tuple[int, ...]]:
    # Při shodném skóre preferujeme lexikograficky menší kombinaci.
    return candidate.score.total_score, tuple(-number for number in candidate.numbers)


def _deterministic_reserve_priority(numbers: NumberTuple) -> int:
    """Rychlý stabilní 64bit mix pro deterministickou průřezovou rezervu."""
    value = 0x9E3779B97F4A7C15
    mask = (1 << 64) - 1
    for number in numbers:
        value ^= (number + 0x9E3779B9 + ((value << 6) & mask) + (value >> 2)) & mask
        value = (value * 0xBF58476D1CE4E5B9) & mask
    value ^= value >> 30
    value = (value * 0xBF58476D1CE4E5B9) & mask
    value ^= value >> 27
    value = (value * 0x94D049BB133111EB) & mask
    return value ^ (value >> 31)


def _push_top_candidate(
    heap: list[tuple[float, tuple[int, ...], CombinationCandidate]],
    candidate: CombinationCandidate,
    capacity: int,
) -> None:
    if capacity <= 0:
        return
    item = (*_score_heap_key(candidate), candidate)
    if len(heap) < capacity:
        heapq.heappush(heap, item)
    elif item[:2] > heap[0][:2]:
        heapq.heapreplace(heap, item)


def _push_reserve_candidate(
    heap: list[tuple[int, NumberTuple, CombinationCandidate]],
    candidate: CombinationCandidate,
    capacity: int,
) -> None:
    if capacity <= 0:
        return
    item = (_deterministic_reserve_priority(candidate.numbers), candidate.numbers, candidate)
    if len(heap) < capacity:
        heapq.heappush(heap, item)
    elif item[:2] > heap[0][:2]:
        heapq.heapreplace(heap, item)


def _merge_candidate_pool(
    top_heap: list[tuple[float, tuple[int, ...], CombinationCandidate]],
    reserve_heap: list[tuple[int, NumberTuple, CombinationCandidate]],
    *,
    max_candidates: int,
    reserve_fraction: float,
) -> list[CombinationCandidate]:
    top = sorted(
        (item[2] for item in top_heap),
        key=lambda candidate: (-candidate.score.total_score, candidate.numbers),
    )
    reserve = sorted(
        (item[2] for item in reserve_heap),
        key=lambda candidate: (-_deterministic_reserve_priority(candidate.numbers), candidate.numbers),
    )

    reserve_quota = min(max_candidates, round(max_candidates * reserve_fraction))
    top_quota = max_candidates - reserve_quota
    selected: list[CombinationCandidate] = []
    seen: set[NumberTuple] = set()

    for candidate in top[:top_quota]:
        selected.append(candidate)
        seen.add(candidate.numbers)

    for candidate in reserve:
        if len(selected) >= top_quota + reserve_quota:
            break
        if candidate.numbers not in seen:
            selected.append(candidate)
            seen.add(candidate.numbers)

    if len(selected) < max_candidates:
        for candidate in top[top_quota:]:
            if len(selected) >= max_candidates:
                break
            if candidate.numbers not in seen:
                selected.append(candidate)
                seen.add(candidate.numbers)

    selected.sort(key=lambda candidate: (-candidate.score.total_score, candidate.numbers))
    return selected


def build_candidate_pool(
    preset: PresetConfig,
    historical_context: HistoricalContext,
    *,
    generation_mode: str,
    sample_size: int,
    seed: int | None,
    stats: RunStats,
    progress_callback: ProgressCallback | None = None,
    log_progress: bool = True,
) -> CandidatePoolResult:
    """Vytvoří kandidátní pool a průběžně plní ``RunStats``."""
    config = preset.config
    max_candidates = config.scoring.max_candidates_for_diversity
    reserve_capacity = round(max_candidates * config.mmr.diversity_reserve_fraction)
    top_heap: list[tuple[float, tuple[int, ...], CombinationCandidate]] = []
    reserve_heap: list[tuple[int, NumberTuple, CombinationCandidate]] = []
    progress_total = sample_size if generation_mode == SAMPLE_MODE else stats.total_possible
    progress_step = max(50_000, progress_total // 100) if progress_total else 50_000

    start = time.perf_counter()
    for numbers in combination_iterator(preset, generation_mode, sample_size, seed):
        stats.generated += 1
        if stats.generated % progress_step == 0:
            if progress_callback is not None:
                progress_callback(stats.generated, progress_total, stats)
            if log_progress:
                LOGGER.info(
                    "Zpracováno %s / %s kombinací %s | po tvrdých filtrech %s | po skóre %s",
                    f"{stats.generated:,}",
                    f"{progress_total:,}",
                    format_progress_bar(stats.generated, progress_total),
                    f"{stats.passed_hard_filters:,}",
                    f"{stats.passed_min_score:,}",
                )

        metrics = calculate_combination_metrics(
            numbers,
            config,
            historical_context,
            include_historical_overlap=False,
        )
        structural_result = apply_structural_filters(numbers, metrics, config)
        if not structural_result.passed:
            stats.add_filter_failure(structural_result.failed_filter or "unknown")
            continue

        metrics = add_historical_overlap(metrics, historical_context)
        historical_result = apply_historical_filters(numbers, metrics, historical_context, config)
        filter_result = merge_filter_results(structural_result, historical_result)
        if not filter_result.passed:
            stats.add_filter_failure(filter_result.failed_filter or "unknown")
            continue

        stats.passed_hard_filters += 1
        score = score_combination(metrics, historical_context, config)
        if score.total_score < config.scoring.min_score_to_keep:
            continue

        stats.passed_min_score += 1
        candidate = CombinationCandidate(
            numbers=numbers,
            metrics=metrics,
            filter_result=filter_result,
            score=score,
        )
        _push_top_candidate(top_heap, candidate, max_candidates)
        _push_reserve_candidate(reserve_heap, candidate, reserve_capacity)

    if progress_callback is not None:
        progress_callback(stats.generated, progress_total, stats)

    candidates = _merge_candidate_pool(
        top_heap,
        reserve_heap,
        max_candidates=max_candidates,
        reserve_fraction=config.mmr.diversity_reserve_fraction,
    )
    stats.kept_for_diversity = len(candidates)
    return CandidatePoolResult(candidates=candidates, duration_seconds=time.perf_counter() - start)
