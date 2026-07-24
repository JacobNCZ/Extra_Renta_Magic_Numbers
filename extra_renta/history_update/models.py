"""Modely pro aktualizaci historických tahů Extra Renty."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.models import NumberTuple


@dataclass(frozen=True)
class FetchedDraw:
    """Jeden tah získaný z externího zdroje."""

    date: str
    numbers: NumberTuple
    source: str = "official"


@dataclass(frozen=True)
class HistoryUpdatePreview:
    """Souhrn porovnání externího zdroje a lokální historie."""

    fetched_draws: tuple[FetchedDraw, ...]
    new_draws: tuple[FetchedDraw, ...]
    existing_draws: tuple[FetchedDraw, ...]
    conflicting_draws: tuple[FetchedDraw, ...]
    invalid_draws: tuple[FetchedDraw, ...]
    source_url: str
    source_error: str | None = None
    source_errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_new_draws(self) -> bool:
        """Vrátí True, pokud zdroj obsahuje nové validní tahy."""
        return bool(self.new_draws)


@dataclass(frozen=True)
class HistoryUpdateApplyResult:
    """Výsledek zápisu aktualizovaných historických dat."""

    preview: HistoryUpdatePreview
    updated: bool
    backup_path: str | None = None
    target_path: str | None = None
    message: str = ""
