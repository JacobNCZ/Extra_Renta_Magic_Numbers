"""Deterministický MMR / marginal-gain greedy výběr finálního portfolia.

Algoritmus kombinuje individuální skóre kandidáta s jeho marginálním přínosem
pro již vybranou sadu. Používá lazy-greedy haldu: dynamické přínosy jsou
monotónně neklesající směrem dolů, takže není nutné po každém výběru přepočítat
všech 100 000 kandidátů.
"""

from __future__ import annotations

import heapq
import itertools
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace

from .models import (
    AppConfig,
    CombinationCandidate,
    DiversityDiagnostics,
    DiversitySelectionResult,
    NumberTuple,
    SelectionBreakdown,
)

SelectionProgressCallback = Callable[[int, int], None]
_EPSILON = 1e-12


@dataclass(frozen=True, slots=True)
class _CandidateFeatures:
    candidate: CombinationCandidate
    pairs: tuple[tuple[int, int], ...]
    triplets: tuple[tuple[int, int, int], ...]
    overlap_guard_subsets: tuple[NumberTuple, ...]
    normalized_score: float


def _overlap_guard_subsets(numbers: NumberTuple, max_overlap: int) -> tuple[NumberTuple, ...]:
    subset_size = max_overlap + 1
    if subset_size <= 0 or subset_size > len(numbers):
        return ()
    return tuple(itertools.combinations(numbers, subset_size))


def _features(candidate: CombinationCandidate, config: AppConfig) -> _CandidateFeatures:
    numbers = candidate.numbers
    max_score = max(config.scoring.max_score, _EPSILON)
    return _CandidateFeatures(
        candidate=candidate,
        pairs=tuple(itertools.combinations(numbers, 2)),
        triplets=(
            tuple(itertools.combinations(numbers, 3))
            if config.diversity.enforce_pair_triplet_limits
            else ()
        ),
        overlap_guard_subsets=_overlap_guard_subsets(
            numbers,
            config.diversity.max_overlap_between_selected,
        ),
        normalized_score=max(0.0, min(1.0, candidate.score.total_score / max_score)),
    )


def _is_feasible(
    item: _CandidateFeatures,
    config: AppConfig,
    forbidden_overlap_subsets: set[NumberTuple],
    pair_counter: Counter[tuple[int, int]],
    triplet_counter: Counter[tuple[int, int, int]],
) -> tuple[bool, str | None]:
    if item.overlap_guard_subsets and any(
        subset in forbidden_overlap_subsets for subset in item.overlap_guard_subsets
    ):
        return False, "overlap"

    diversity = config.diversity
    if diversity.enforce_pair_triplet_limits:
        if any(pair_counter[pair] >= diversity.max_pair_reuse for pair in item.pairs):
            return False, "pair_reuse"
        if any(triplet_counter[triplet] >= diversity.max_triplet_reuse for triplet in item.triplets):
            return False, "triplet_reuse"
    return True, None


def _marginal_breakdown(
    item: _CandidateFeatures,
    config: AppConfig,
    number_counter: Counter[int],
    pair_counter: Counter[tuple[int, int]],
) -> SelectionBreakdown:
    """Vrátí normalizovaný přínos kandidáta v aktuálním stavu portfolia."""
    numbers = item.candidate.numbers
    pairs = item.pairs

    # Reciproká odměna přirozeně preferuje méně používaná čísla a s každým
    # dalším výskytem monotónně klesá. To umožňuje korektní lazy-greedy haldu.
    number_balance = sum(1.0 / (1.0 + number_counter[number]) for number in numbers) / len(numbers)

    new_pairs = sum(1 for pair in pairs if pair_counter[pair] == 0)
    pair_coverage = new_pairs / len(pairs) if pairs else 0.0

    overlap_diversity = (
        sum(1.0 / (1.0 + pair_counter[pair]) for pair in pairs) / len(pairs)
        if pairs
        else 0.0
    )
    max_pair_reuse_before = max((pair_counter[pair] for pair in pairs), default=0)
    pair_reuse_safety = 1.0 / (1.0 + max_pair_reuse_before)

    mmr = config.mmr
    marginal_gain = (
        mmr.score_weight * item.normalized_score
        + mmr.number_balance_weight * number_balance
        + mmr.pair_coverage_weight * pair_coverage
        + mmr.overlap_diversity_weight * overlap_diversity
        + mmr.pair_reuse_safety_weight * pair_reuse_safety
    )
    return SelectionBreakdown(
        marginal_gain=marginal_gain,
        normalized_score=item.normalized_score,
        number_balance=number_balance,
        pair_coverage=pair_coverage,
        overlap_diversity=overlap_diversity,
        pair_reuse_safety=pair_reuse_safety,
        new_pairs=new_pairs,
        max_pair_reuse_before=max_pair_reuse_before,
    )


def _heap_item(
    index: int,
    item: _CandidateFeatures,
    breakdown: SelectionBreakdown,
) -> tuple[float, float, float, float, NumberTuple, int, SelectionBreakdown]:
    """Deterministické pořadí: gain, původní skóre, nové páry, balance, čísla."""
    return (
        -breakdown.marginal_gain,
        -item.normalized_score,
        -breakdown.pair_coverage,
        -breakdown.number_balance,
        item.candidate.numbers,
        index,
        breakdown,
    )


def select_candidates_with_mmr(
    candidates: list[CombinationCandidate],
    config: AppConfig,
    *,
    progress_callback: SelectionProgressCallback | None = None,
) -> DiversitySelectionResult:
    """Vybere nejvýše ``max_output_count`` kandidátů pomocí lazy MMR."""
    max_output = config.diversity.max_output_count
    diagnostics = DiversityDiagnostics(
        max_output_count=max_output,
        candidates_considered=len(candidates),
        selection_strategy="mmr",
    )
    if progress_callback is not None:
        progress_callback(0, max_output)

    if max_output <= 0 or not candidates:
        diagnostics.stop_reason = "empty_candidate_pool"
        return DiversitySelectionResult(selected=[], diagnostics=diagnostics)

    feature_items = [_features(candidate, config) for candidate in candidates]
    number_counter: Counter[int] = Counter()
    pair_counter: Counter[tuple[int, int]] = Counter()
    triplet_counter: Counter[tuple[int, int, int]] = Counter()
    forbidden_overlap_subsets: set[NumberTuple] = set()
    selected: list[CombinationCandidate] = []
    gains: list[float] = []

    heap: list[tuple[float, float, float, float, NumberTuple, int, SelectionBreakdown]] = []
    for index, item in enumerate(feature_items):
        breakdown = _marginal_breakdown(item, config, number_counter, pair_counter)
        heapq.heappush(heap, _heap_item(index, item, breakdown))
        diagnostics.mmr_candidate_evaluations += 1

    rejected: set[int] = set()
    while heap and len(selected) < max_output:
        *_, index, cached_breakdown = heapq.heappop(heap)
        if index in rejected:
            continue
        item = feature_items[index]
        feasible, reason = _is_feasible(
            item,
            config,
            forbidden_overlap_subsets,
            pair_counter,
            triplet_counter,
        )
        if not feasible:
            rejected.add(index)
            if reason == "overlap":
                diagnostics.rejected_overlap += 1
            elif reason == "pair_reuse":
                diagnostics.rejected_pair_reuse += 1
            elif reason == "triplet_reuse":
                diagnostics.rejected_triplet_reuse += 1
            continue

        current = _marginal_breakdown(item, config, number_counter, pair_counter)
        diagnostics.mmr_candidate_evaluations += 1
        diagnostics.mmr_heap_recomputations += 1

        next_upper_bound = -heap[0][0] if heap else float("-inf")
        if current.marginal_gain + _EPSILON < next_upper_bound:
            heapq.heappush(heap, _heap_item(index, item, current))
            continue

        if current.marginal_gain + _EPSILON < config.mmr.min_marginal_gain:
            diagnostics.stop_reason = "marginal_gain_below_threshold"
            break

        selected_candidate = replace(item.candidate, selection=current)
        selected.append(selected_candidate)
        gains.append(current.marginal_gain)
        number_counter.update(item.candidate.numbers)
        pair_counter.update(item.pairs)
        if item.triplets:
            triplet_counter.update(item.triplets)
        if item.overlap_guard_subsets:
            forbidden_overlap_subsets.update(item.overlap_guard_subsets)

        if progress_callback is not None:
            progress_callback(len(selected), max_output)

    diagnostics.selected_count = len(selected)
    if len(selected) >= max_output:
        diagnostics.stopped_after_reaching_limit = True
        diagnostics.stop_reason = "max_output_limit_reached"
    elif diagnostics.stop_reason == "not_started":
        diagnostics.stop_reason = "no_feasible_candidate" if rejected else "candidate_pool_exhausted"

    if gains:
        diagnostics.mmr_average_gain = sum(gains) / len(gains)
        diagnostics.mmr_min_gain = min(gains)
        diagnostics.mmr_max_gain = max(gains)

    if progress_callback is not None and len(selected) < max_output:
        progress_callback(len(selected), max_output)
    return DiversitySelectionResult(selected=selected, diagnostics=diagnostics)
