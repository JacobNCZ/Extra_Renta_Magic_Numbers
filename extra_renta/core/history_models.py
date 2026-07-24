"""Modely historických tahů a validačního kontextu."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

NumberTuple = tuple[int, ...]


@dataclass(frozen=True)
class HistoricalDraw:
    """Jeden historický tah po validaci a normalizaci."""

    date: str
    numbers: NumberTuple
    is_valid: bool
    note: str = ""


@dataclass(frozen=True)
class HistoricalContext:
    """Předpočítaný kontext historických dat pro filtry, scoring a statistiku."""

    valid_draws: tuple[HistoricalDraw, ...]
    invalid_draws: tuple[HistoricalDraw, ...]
    exact_combinations: frozenset[NumberTuple]
    draw_sets: tuple[frozenset[int], ...]
    historical_subsets_4: frozenset[NumberTuple]
    historical_subsets_5: frozenset[NumberTuple]
    historical_subsets_6: frozenset[NumberTuple]
    last_valid_draw: HistoricalDraw | None
    last_draw_numbers: frozenset[int] = frozenset()
    last_draw_neighbors: frozenset[int] = frozenset()
    duplicate_dates: tuple[str, ...] = ()
    duplicate_combinations: tuple[NumberTuple, ...] = ()
    date_parse_errors: tuple[str, ...] = ()
    date_order_warnings: tuple[str, ...] = ()
    validation_warnings: tuple[str, ...] = ()

    def validation_summary(self) -> dict[str, Any]:
        """Vrátí rozšířený souhrn validace historických dat."""
        return {
            "valid_draws": len(self.valid_draws),
            "invalid_draws": len(self.invalid_draws),
            "duplicate_dates": list(self.duplicate_dates),
            "duplicate_combinations": [list(numbers) for numbers in self.duplicate_combinations],
            "date_parse_errors": list(self.date_parse_errors),
            "date_order_warnings": list(self.date_order_warnings),
            "validation_warnings": list(self.validation_warnings),
        }
