"""Konzolový výstup pro Extra Renta pipeline."""

from __future__ import annotations

from collections.abc import Iterable

from ..combination_check import CombinationCheckResult
from ..core.models import CombinationCandidate, HistoricalContext, RunStats
from ..core.score_explainer import explain_score_components, format_score_explanation

FILTER_THROUGHPUT_ORDER: tuple[str, ...] = (
    "basic_length",
    "unique_numbers",
    "number_range",
    "sum_range",
    "odd_even_balance",
    "low_high_balance",
    "tier_distribution",
    "tier_concentration",
    "bucket_distribution",
    "bucket_concentration",
    "span_range",
    "max_gap",
    "adjacent_pairs",
    "consecutive_run",
    "last_digit_concentration",
    "exact_historical_draw",
    "historical_overlap",
)

FILTER_LABELS: dict[str, str] = {
    "basic_length": "Správný počet čísel",
    "unique_numbers": "Unikátnost čísel",
    "number_range": "Rozsah čísel",
    "sum_range": "Součet čísel",
    "odd_even_balance": "Sudá / lichá",
    "low_high_balance": "Nízká / vysoká",
    "tier_distribution": "Nízká/střední/vysoká pásma",
    "tier_concentration": "Koncentrace v pásmu",
    "bucket_distribution": "Rozložení do jemnějších pásem",
    "bucket_concentration": "Koncentrace v jemném pásmu",
    "span_range": "Rozpětí kombinace",
    "max_gap": "Maximální mezera",
    "adjacent_pairs": "Sousední dvojice",
    "consecutive_run": "Souvislá sekvence",
    "last_digit_concentration": "Stejná koncovka",
    "exact_historical_draw": "Přesný historický tah",
    "historical_overlap": "Historický překryv",
    "other": "Ostatní",
}

SCORE_COMPONENT_SHORT_LABELS: dict[str, str] = {
    "součet čísel": "součet",
    "sudá / lichá": "sudá/lichá",
    "poměr sudá/lichá": "sudá/lichá",
    "nízká / vysoká": "nízká/vys.",
    "poměr nízká/vysoká": "nízká/vys.",
    "nízká/střední/vysoká pásma": "pásma",
    "rozložení nízká/střední/vysoká": "pásma",
    "rozložení do jemnějších pásem": "jemná pásma",
    "rozpětí kombinace": "rozpětí",
    "mezery mezi čísly": "mezery",
    "historická podobnost": "historie",
    "odolnost proti lidským vzorům": "vzory",
    "odolnost vůči jednoduchým vzorům": "vzory",
    "celková rovnoměrnost": "rovnoměrnost",
}


def _fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _fmt_pct(value: float) -> str:
    return f"{value:.6f} %" if value < 0.01 else f"{value:.4f} %"


def print_disclaimer() -> None:
    """Vypíše stručné upozornění k interpretaci výsledků."""
    print("=== UPOZORNĚNÍ ===")
    print("Program pouze filtruje, skóruje a diverzifikuje kandidátní kombinace.")
    print("Historická data, filtry ani MMR výběr nezvyšují matematickou pravděpodobnost výhry.\n")


def print_historical_summary(context: HistoricalContext) -> None:
    """Vypíše souhrn validovaných historických dat."""
    print("=== HISTORICKÁ DATA ===")
    print(f"Validní tahy:       {_fmt_int(len(context.valid_draws))}")
    print(f"Nevalidní řádky:    {_fmt_int(len(context.invalid_draws))}")
    if context.last_valid_draw:
        print(f"Poslední validní:   {context.last_valid_draw.date} {list(context.last_valid_draw.numbers)}")
    if context.validation_warnings:
        print("Validační upozornění:")
        for warning in context.validation_warnings[:5]:
            print(f"- {warning}")
    print()


def _is_small_sample(stats: RunStats, max_output_count: int) -> bool:
    """Vrátí True, když je diagnostický vzorek menší než limit výstupu."""
    return stats.sample_size is not None and stats.generated < max_output_count

def build_next_step_recommendation(stats: RunStats, max_output_count: int) -> str:
    """Vrátí praktické doporučení bez interpretace maxima jako povinného cíle."""
    if stats.generated == 0:
        return "Nebyla vygenerována žádná kombinace. Ověř konfiguraci generátoru."
    if stats.final_selected == 0:
        if stats.passed_hard_filters == 0:
            return "Žádná kombinace neprošla tvrdými filtry. Zvaž mírnější předvolbu."
        if stats.passed_min_score == 0:
            return "Kombinace prošly filtry, ale ne minimálním skóre. Zvaž mírnější scoring."
        return "Kandidáti existují, ale žádný nesplnil finální tvrdé portfolio limity."
    if stats.output_limit_reached(max_output_count):
        return "Byl dosažen maximální limit výstupu. Výsledek je připraven ke kontrole a exportu."
    reason = stats.diversity_diagnostics.stop_reason
    if reason == "marginal_gain_below_threshold":
        return "Výběr skončil, protože další kandidát nepřinesl požadovaný marginální přínos."
    if _is_small_sample(stats, max_output_count):
        return "Výsledek pochází z menšího diagnostického vzorku; pro finální běh použij kompletní průchod."
    return "Menší počet než maximální limit je platný. Výběr skončil po vyčerpání přípustných kandidátů."

def evaluate_strictness(stats: RunStats, max_output_count: int) -> tuple[str, ...]:
    """Vrátí praktická upozornění k přísnosti pravidel po běhu."""
    messages: list[str] = []
    if stats.generated == 0:
        return ("Nebyly vygenerovány žádné kombinace, přísnost nelze vyhodnotit.",)

    hard_filter_ratio = stats.passed_hard_filters / stats.generated
    score_ratio = stats.passed_min_score / stats.generated
    if _is_small_sample(stats, max_output_count):
        messages.append("Diagnostický vzorek je menší než maximální limit výstupu.")
    if stats.passed_hard_filters == 0:
        messages.append("Tvrdé filtry jsou příliš přísné: neprošla žádná kombinace.")
    elif hard_filter_ratio < 0.001:
        messages.append("Tvrdé filtry propustily méně než 0,1 % zpracovaných kombinací.")
    if stats.passed_min_score == 0:
        messages.append("Po minimálním skóre nezůstal žádný kandidát pro MMR výběr.")
    elif score_ratio < 0.0005:
        messages.append("Po skórování zůstalo méně než 0,05 % zpracovaných kombinací.")
    if stats.kept_for_diversity == 0:
        messages.append("Kandidátní pool je prázdný.")
    if not messages:
        messages.append("Nastavení je po tomto běhu použitelné; menší počet než limit není chyba.")
    return tuple(messages)

def print_filter_throughput(stats: RunStats) -> None:
    """Vypíše propustnost tvrdých filtrů po jednotlivých pravidlech."""
    print("=== PROPUSTNOST TVRDÝCH FILTRŮ ===")
    print(f"{'Filtr':<34} {'Zamítnuto':>12} {'Zůstává':>12} {'% ze zprac.':>13}")
    print("-" * 77)
    for row in stats.filter_throughput(FILTER_THROUGHPUT_ORDER):
        rejected = int(row["rejected"])
        if rejected == 0 and row["filter"] in {"basic_length", "unique_numbers", "number_range"}:
            continue
        label = FILTER_LABELS.get(str(row["filter"]), str(row["filter"]))
        print(
            f"{label:<34} "
            f"{_fmt_int(rejected):>12} "
            f"{_fmt_int(int(row['passed_after_filter'])):>12} "
            f"{float(row['passed_after_filter_pct_of_generated']):>12.4f} %"
        )
    print(f"{'Po všech tvrdých filtrech':<34} {'':>12} {_fmt_int(stats.passed_hard_filters):>12} {stats.percent_of_generated(stats.passed_hard_filters):>12.4f} %")
    print()


def print_strictness_check(stats: RunStats, max_output_count: int) -> None:
    """Vypíše kontrolu praktické přísnosti pravidel."""
    stats.strictness_warnings = evaluate_strictness(stats, max_output_count)
    print("=== KONTROLA PŘÍSNOSTI PRAVIDEL ===")
    for message in stats.strictness_warnings:
        print(f"- {message}")
    print()

def print_run_stats(stats: RunStats) -> None:
    """Vypíše hlavní statistiku zúžení prostoru a MMR diagnostiku."""
    print("=== STATISTIKA BĚHU ===")
    print(f"Režim generování:             {stats.generation_mode}")
    if stats.sample_size is not None:
        print(f"Velikost diagnostického vzorku: {_fmt_int(stats.sample_size)}")
    if stats.random_seed is not None:
        print(f"Seed vzorkování:              {stats.random_seed}")
    print(f"Všech možných kombinací:      {_fmt_int(stats.total_possible):>12} | 100.0000 %")
    print(f"Skutečně vygenerováno:        {_fmt_int(stats.generated):>12} | {_fmt_pct(stats.percent_of_total(stats.generated))}")
    print(f"Po tvrdých filtrech:          {_fmt_int(stats.passed_hard_filters):>12} | {_fmt_pct(stats.percent_of_total(stats.passed_hard_filters))}")
    print(f"Po minimálním skóre:          {_fmt_int(stats.passed_min_score):>12} | {_fmt_pct(stats.percent_of_total(stats.passed_min_score))}")
    print(f"Ponecháno pro MMR:            {_fmt_int(stats.kept_for_diversity):>12} | {_fmt_pct(stats.percent_of_total(stats.kept_for_diversity))}")
    print(f"Finálně vybráno:              {_fmt_int(stats.final_selected):>12} | {_fmt_pct(stats.percent_of_total(stats.final_selected))}")
    if stats.benchmark.total_seconds > 0:
        print("\nBenchmark výkonu:")
        print(f"- Celkem:                     {stats.benchmark.total_seconds:.3f} s")
        print(f"- Filtry + scoring:           {stats.benchmark.generation_filter_scoring_seconds:.3f} s")
        print(f"- MMR výběr:                  {stats.benchmark.selection_seconds:.3f} s")
        print(f"- Export:                     {stats.benchmark.export_seconds:.3f} s")
        print(f"- Kombinací za sekundu:       {stats.benchmark.combinations_per_second:.1f}")

    diagnostics = stats.diversity_diagnostics
    print("\nMMR portfolio výběr:")
    print(f"- Maximální limit výstupu:    {_fmt_int(diagnostics.max_output_count)}")
    print(f"- Zvažováno kandidátů:        {_fmt_int(diagnostics.candidates_considered)}")
    print(f"- Zamítnuto kvůli překryvu:   {_fmt_int(diagnostics.rejected_overlap)}")
    print(f"- Zamítnuto kvůli dvojicím:   {_fmt_int(diagnostics.rejected_pair_reuse)}")
    print(f"- Zamítnuto kvůli trojicím:   {_fmt_int(diagnostics.rejected_triplet_reuse)}")
    print(f"- Dosažen maximální limit:    {'ano' if diagnostics.stopped_after_reaching_limit else 'ne'}")
    print(f"- Důvod ukončení:             {diagnostics.stop_reason}")
    print(f"- MMR přepočtů:               {_fmt_int(diagnostics.mmr_heap_recomputations)}")
    if diagnostics.mmr_average_gain is not None:
        print(f"- Průměrný marginální přínos: {diagnostics.mmr_average_gain:.4f}")
    print()

def print_output_limit_info(stats: RunStats, max_output_count: int) -> None:
    """Vysvětlí vztah skutečného výstupu k hornímu limitu."""
    print("=== LIMIT VÝSTUPU ===")
    print(f"Maximální limit:    {_fmt_int(max_output_count)}")
    print(f"Skutečně vybráno:   {_fmt_int(stats.final_selected)}")
    print(f"Důvod ukončení:     {stats.diversity_diagnostics.stop_reason}")
    if stats.final_selected < max_output_count:
        print("Menší počet je platný výsledek; maximální limit není povinný cíl.")
    print()

def print_final_summary(stats: RunStats, max_output_count: int) -> None:
    """Vypíše krátké závěrečné shrnutí."""
    status = "LIMIT DOSAŽEN" if stats.output_limit_reached(max_output_count) else "VÝBĚR UKONČEN DŘÍVE"
    print("=== ZÁVĚREČNÉ SHRNUTÍ ===")
    print(f"Stav:              {status}")
    print(f"Finálně vybráno:   {_fmt_int(stats.final_selected)} / max {_fmt_int(max_output_count)}")
    print(f"Doporučený krok:   {build_next_step_recommendation(stats, max_output_count)}")
    print()

def _top_score_components(candidate: CombinationCandidate, *, limit: int = 3) -> str:
    """Vrátí krátký přehled nejsilnějších složek skóre pro konzoli."""
    components = sorted(
        explain_score_components(candidate),
        key=lambda item: float(item["points"]),
        reverse=True,
    )
    labels = [
        SCORE_COMPONENT_SHORT_LABELS.get(str(item["label"]), str(item["label"]))
        for item in components[:limit]
    ]
    return ",".join(labels)


def _format_numbers_inline(numbers: Iterable[int]) -> str:
    """Vrátí kompaktní zápis kombinace pro jednořádkový výpis."""
    return " ".join(f"{number:02d}" for number in numbers)


def _yes_no(value: bool) -> str:
    return "ano" if value else "ne"


def print_top_candidates(
    candidates: Iterable[CombinationCandidate],
    *,
    limit: int = 10,
    show_score_breakdown: bool = False,
) -> None:
    """Vypíše několik nejlépe skórovaných finálních kandidátů."""
    print("=== TOP FINÁLNÍ KANDIDÁTI S VYSVĚTLENÍM SKÓRE ===")
    printed = 0
    for rank, candidate in enumerate(candidates, start=1):
        if rank > limit:
            break
        printed += 1
        numbers = _format_numbers_inline(candidate.numbers)
        top_components = _top_score_components(candidate)
        print(
            f"{rank:>2}. [{numbers}] | sk {candidate.score.total_score:>5.1f} | "
            f"S{candidate.metrics.total_sum:>3} R{candidate.metrics.span:>2} | top {top_components}"
        )
        if show_score_breakdown:
            print(f"     kompletní rozpad: {format_score_explanation(candidate)}")
    if printed == 0:
        print("Žádný kandidát nebyl vybrán.")
    print()


def print_combination_check_result(result: CombinationCheckResult) -> None:
    """Vypíše kontrolu vlastní kombinace proti aktuálnímu běhu."""
    print("=== KONTROLA VLASTNÍ KOMBINACE ===")
    if result.numbers:
        print(f"Kombinace:                    [{_format_numbers_inline(result.numbers)}]")
    else:
        print(f"Kombinace:                    {result.raw_input!r}")

    print(f"Validní vstup:                {_yes_no(result.is_valid_input)}")
    for error in result.input_errors:
        print(f"- {error}")

    if not result.is_valid_input:
        print(f"Výsledek:                     {result.reason}")
        print()
        return

    if result.filter_result is not None:
        print(f"Tvrdé filtry:                 {'prošla' if result.filter_result.passed else 'neprošla'}")
        if result.filter_result.failed_filter:
            label = FILTER_LABELS.get(result.filter_result.failed_filter, result.filter_result.failed_filter)
            print(f"Neprošla filtrem:             {label}")

    if result.score is not None:
        print(f"Skóre:                        {result.score.total_score:.2f}")
        print(f"Splňuje minimální skóre:      {_yes_no(result.passes_min_score)}")
    else:
        print("Skóre:                        nepočítáno, protože kombinace neprošla tvrdými filtry")

    if result.metrics is not None:
        print(f"Součet / rozpětí:             {result.metrics.total_sum} / {result.metrics.span}")

    pool_rank = f"ano, pořadí {result.candidate_pool_rank}" if result.candidate_pool_rank else _yes_no(False)
    final_rank = f"ano, pořadí {result.final_rank}" if result.final_rank else _yes_no(False)
    print(f"V užším kandidátním poolu:    {pool_rank}")
    print(f"Ve finálním výběru:           {final_rank}")
    if result.closest_selected_overlap is not None:
        print(f"Nejvyšší překryv s finálem:   {result.closest_selected_overlap} čísel")
    print(f"Výsledek:                     {result.reason}")
    print()


def format_progress_bar(current: int, total: int, *, width: int = 28) -> str:
    """Vrátí jednoduchý textový progress bar."""
    if total <= 0:
        return "[" + "?" * width + "]"
    ratio = min(max(current / total, 0.0), 1.0)
    filled = int(width * ratio)
    return "[" + "#" * filled + "." * (width - filled) + f"] {ratio * 100:5.1f} %"
