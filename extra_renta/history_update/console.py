"""Konzolový výstup pro aktualizaci historických tahů."""

from __future__ import annotations

from collections.abc import Iterable

from ..combination_check import CombinationCheckResult
from .models import FetchedDraw, HistoryUpdateApplyResult, HistoryUpdatePreview


def format_numbers(numbers: Iterable[int]) -> str:
    """Naformátuje čísla jako kuličkovou kombinaci v textu."""
    return "[" + " ".join(f"{number:02d}" for number in numbers) + "]"


def print_history_update_preview(preview: HistoryUpdatePreview) -> None:
    """Vypíše souhrn dostupných nových tahů."""
    print("=== KONTROLA DOSTUPNÝCH NOVÝCH TAHŮ ===")
    print(f"Zdroj:                 {preview.source_url}")
    if preview.source_error:
        print(f"Chyba zdroje:          {preview.source_error}")
        if preview.source_errors:
            print("\nDiagnostika zdrojů:")
            for error in preview.source_errors:
                print(f"- {error}")
        print("Aktualizace nebyla provedena. Zkontroluj dostupnost internetu nebo parser zdroje.\n")
        return

    if preview.source_errors:
        print("Poznámka: primární zdroj neobsahoval parsovatelná čísla, použil se záložní zdroj.")
        print("Předchozí pokusy:")
        for error in preview.source_errors:
            print(f"- {error}")
        print()

    print(f"Staženo tahů:          {len(preview.fetched_draws)}")
    print(f"Nové tahy:             {len(preview.new_draws)}")
    print(f"Již existující tahy:   {len(preview.existing_draws)}")
    print(f"Konfliktní tahy:       {len(preview.conflicting_draws)}")
    print(f"Nevalidní tahy:        {len(preview.invalid_draws)}")

    if preview.new_draws:
        print("\nNové tahy k případnému uložení:")
        for draw in preview.new_draws:
            print(f"- {draw.date}: {format_numbers(draw.numbers)}")
    if preview.conflicting_draws:
        print("\nPozor: některé tahy mají stejné datum jako lokální historie, ale jiná čísla:")
        for draw in preview.conflicting_draws:
            print(f"- {draw.date}: {format_numbers(draw.numbers)}")
    print()


def print_new_draw_checks(results: Iterable[tuple[FetchedDraw, CombinationCheckResult]]) -> None:
    """Vypíše kontrolu nových tahů proti filtrům a scoringu."""
    print("=== KONTROLA NOVÝCH TAHŮ PROTI FILTRŮM A SCORINGU ===")
    print("Poznámka: Jde pouze o zpětnou diagnostiku pravidel, ne o predikci výhry.\n")
    any_result = False
    for draw, check in results:
        any_result = True
        print(f"Datum tahu:                  {draw.date}")
        print(f"Kombinace:                   {format_numbers(draw.numbers)}")
        print(f"Validní vstup:               {'ano' if check.is_valid_input else 'ne'}")
        print(f"Tvrdé filtry:                {'prošla' if check.hard_filters_passed else 'neprošla'}")
        if check.score is not None:
            print(f"Skóre:                       {check.score.total_score:.2f}")
        print(f"Splňuje minimální skóre:     {'ano' if check.passes_min_score else 'ne'}")
        print(f"V užším kandidátním poolu:   {'ano' if check.in_candidate_pool else 'ne'}")
        print(f"Ve finálním výběru:          {'ano' if check.in_final_selection else 'ne'}")
        print(f"Výsledek:                    {check.reason}")
        print("-" * 72)
    if not any_result:
        print("Nejsou dostupné žádné nové tahy ke kontrole.\n")


def print_history_update_apply_result(result: HistoryUpdateApplyResult) -> None:
    """Vypíše výsledek zápisu historických dat."""
    print("=== VÝSLEDEK AKTUALIZACE HISTORIE ===")
    print(result.message)
    if result.updated:
        print(f"Cílový soubor: {result.target_path}")
        if result.backup_path:
            print(f"Záloha:        {result.backup_path}")
    print()
