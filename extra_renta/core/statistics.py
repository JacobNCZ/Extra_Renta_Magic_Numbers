"""Statistické a analytické funkce.

Historická data zde slouží pouze ke kontrole kvality, popisu a porovnání.
Nejde o predikční model budoucích losování.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import replace
from datetime import datetime

from .models import (
    AppConfig,
    CombinationMetrics,
    HistoricalContext,
    HistoricalDraw,
    NumberTuple,
)


def normalize_numbers(numbers: Iterable[object]) -> NumberTuple:
    """Vrátí seřazenou tuple reprezentaci kombinace.

    Tato funkce je vhodná pro validované vstupy. Pro surová historická data se
    používá ``normalize_numbers_for_validation()``, která nečíselné hodnoty
    zachytí jako validační chyby místo pádu programu.
    """
    return tuple(sorted(int(number) for number in numbers))


def normalize_numbers_for_validation(numbers: object) -> tuple[NumberTuple, tuple[str, ...]]:
    """Normalizuje surový seznam čísel a vrátí i nalezené chyby.

    Historická data mohou obsahovat prázdné buňky, text nebo jiné nečekané
    hodnoty. Tyto hodnoty nesmí shodit program; mají být uvedené ve validačním
    reportu a daný řádek se nepoužije pro historické filtry.
    """
    normalized: list[int] = []
    errors: list[str] = []

    if isinstance(numbers, str):
        # Podpora surových hodnot z CSV/Excelu, například:
        # "1, 5, 8, 12, 18, 24, 31" nebo "1;5;8;12;18;24;31".
        iterator = (item.strip() for item in numbers.replace(";", ",").split(","))
    else:
        try:
            iterator = iter(numbers)  # type: ignore[arg-type]
        except TypeError:
            return (), (f"čísla nejsou iterovatelný seznam: {numbers!r}",)

    for value in iterator:
        if value == "":
            errors.append("prázdná hodnota čísla")
            continue
        try:
            normalized.append(int(value))
        except (TypeError, ValueError):
            errors.append(f"nečíselná hodnota: {value!r}")

    return tuple(sorted(normalized)), tuple(errors)


def population_std(values: Sequence[int]) -> float:
    """Populační směrodatná odchylka pro malé seznamy mezer."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def count_range(numbers: NumberTuple, range_: tuple[int, int]) -> int:
    """Spočítá, kolik čísel spadá do zadaného uzavřeného intervalu."""
    start, end = range_
    return sum(1 for number in numbers if start <= number <= end)


def count_ranges(numbers: NumberTuple, ranges: Sequence[tuple[int, int]]) -> tuple[int, ...]:
    """Spočítá rozdělení čísel do více uzavřených intervalů."""
    return tuple(count_range(numbers, range_) for range_ in ranges)


def max_consecutive_run_length(numbers: NumberTuple) -> int:
    """Vrátí délku nejdelší souvislé řady po sobě jdoucích čísel."""
    if not numbers:
        return 0

    current = 1
    maximum = 1
    for previous, current_number in zip(numbers, numbers[1:], strict=False):
        if current_number - previous == 1:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 1
    return maximum


def adjacent_pair_count(numbers: NumberTuple) -> int:
    """Spočítá počet sousedních dvojic, například 12–13."""
    return sum(1 for a, b in zip(numbers, numbers[1:], strict=False) if b - a == 1)


def last_draw_neighbors(last_draw: NumberTuple | None, min_number: int, max_number: int) -> frozenset[int]:
    """Vrátí čísla ±1 od posledního validního tahu."""
    if not last_draw:
        return frozenset()

    neighbors: set[int] = set()
    for number in last_draw:
        if number - 1 >= min_number:
            neighbors.add(number - 1)
        if number + 1 <= max_number:
            neighbors.add(number + 1)
    return frozenset(neighbors)


def build_historical_context(raw_draws: list[dict], config: AppConfig) -> HistoricalContext:
    """Validuje a připraví historická data pro filtry a analytiku.

    Validace kontroluje počet čísel, duplicity, rozsah, ISO datum, duplicitní
    datumy/kombinace a pořadí zdrojových řádků. Nevalidní řádky se nevyhazují
    z evidence, ale nepoužijí se v historických filtrech vyžadujících přesně
    7 čísel v rozsahu 1–33.
    """
    valid_draws: list[HistoricalDraw] = []
    invalid_draws: list[HistoricalDraw] = []
    gen = config.generator

    seen_dates: Counter[str] = Counter()
    seen_combinations: Counter[NumberTuple] = Counter()
    parsed_dates: list[datetime] = []
    date_parse_errors: list[str] = []
    date_order_warnings: list[str] = []

    previous_date: datetime | None = None
    for index, row in enumerate(raw_draws, start=1):
        date = str(row.get("date", ""))
        raw_numbers = row.get("numbers", [])
        numbers, number_errors = normalize_numbers_for_validation(raw_numbers)
        note_parts: list[str] = list(number_errors)

        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            parsed_dates.append(parsed_date)
            if previous_date is not None and parsed_date < previous_date:
                warning = f"řádek {index}: datum {date} je starší než předchozí záznam"
                date_order_warnings.append(warning)
                note_parts.append("datum není ve vstupním pořadí")
            previous_date = parsed_date
        except ValueError:
            date_parse_errors.append(date)
            note_parts.append("nevalidní datum, očekáván formát YYYY-MM-DD")

        if len(numbers) != gen.pick_count:
            note_parts.append(f"očekáváno {gen.pick_count} čísel, nalezeno {len(numbers)}")

        if len(set(numbers)) != len(numbers):
            note_parts.append("duplicitní čísla")

        if any(number < gen.number_min or number > gen.number_max for number in numbers):
            note_parts.append("číslo mimo povolený rozsah")

        seen_dates[date] += 1

        is_valid = not note_parts
        if is_valid:
            seen_combinations[numbers] += 1

        draw = HistoricalDraw(
            date=date,
            numbers=numbers,
            is_valid=is_valid,
            note="; ".join(note_parts),
        )

        if is_valid:
            valid_draws.append(draw)
        else:
            invalid_draws.append(draw)

    duplicate_dates = tuple(sorted(date for date, count in seen_dates.items() if count > 1 and date))
    duplicate_combinations = tuple(
        sorted((numbers for numbers, count in seen_combinations.items() if count > 1), key=lambda nums: nums)
    )

    validation_warnings: list[str] = []
    if duplicate_dates:
        validation_warnings.append(f"Nalezeno duplicitních datumů: {len(duplicate_dates)}")
    if duplicate_combinations:
        validation_warnings.append(f"Nalezeno duplicitních kombinací: {len(duplicate_combinations)}")
    if date_parse_errors:
        validation_warnings.append(f"Nalezeno datumů s chybným formátem: {len(date_parse_errors)}")
    if date_order_warnings:
        validation_warnings.append(f"Nalezeno problémů s pořadím dat: {len(date_order_warnings)}")

    valid_draws.sort(key=lambda draw: draw.date)
    invalid_draws.sort(key=lambda draw: draw.date)

    exact_combinations = frozenset(draw.numbers for draw in valid_draws)
    draw_sets = tuple(frozenset(draw.numbers) for draw in valid_draws)

    # Optimalizace historické podobnosti:
    # Při kompletním průchodu 4,27M kombinací by bylo pomalé porovnávat každou
    # kombinaci se všemi historickými tahy. Proto předpočítáme historické
    # podmnožiny velikosti 4, 5 a 6. Kandidát pak otestuje jen své vlastní
    # malé množství podmnožin: C(7,4), C(7,5), C(7,6).
    historical_subsets_4 = frozenset(
        tuple(subset)
        for draw in valid_draws
        for subset in itertools.combinations(draw.numbers, 4)
    )
    historical_subsets_5 = frozenset(
        tuple(subset)
        for draw in valid_draws
        for subset in itertools.combinations(draw.numbers, 5)
    )
    historical_subsets_6 = frozenset(
        tuple(subset)
        for draw in valid_draws
        for subset in itertools.combinations(draw.numbers, 6)
    )

    last_valid_draw = valid_draws[-1] if valid_draws else None

    return HistoricalContext(
        valid_draws=tuple(valid_draws),
        invalid_draws=tuple(invalid_draws),
        exact_combinations=exact_combinations,
        draw_sets=draw_sets,
        historical_subsets_4=historical_subsets_4,
        historical_subsets_5=historical_subsets_5,
        historical_subsets_6=historical_subsets_6,
        last_valid_draw=last_valid_draw,
        last_draw_numbers=frozenset(last_valid_draw.numbers) if last_valid_draw else frozenset(),
        last_draw_neighbors=last_draw_neighbors(
            last_valid_draw.numbers if last_valid_draw else None,
            gen.number_min,
            gen.number_max,
        ),
        duplicate_dates=duplicate_dates,
        duplicate_combinations=duplicate_combinations,
        date_parse_errors=tuple(date_parse_errors),
        date_order_warnings=tuple(date_order_warnings),
        validation_warnings=tuple(validation_warnings),
    )

def max_historical_overlap(numbers: NumberTuple, context: HistoricalContext) -> int:
    """Vrátí nejvyšší doloženou podobnost s validní historií.

    Funkce je optimalizovaná pro kompletní průchod všemi kombinacemi. Nehledá
    podobnost iterací přes všechny historické tahy, ale používá předpočítané
    historické podmnožiny 4/5/6 čísel. Pro scoring je přesnost v pásmu 0–3
    zbytečná, proto vrací 0, pokud nenajde ani shodu 4 čísel.
    """
    if not context.valid_draws:
        return 0

    if numbers in context.exact_combinations:
        return 7

    for subset in itertools.combinations(numbers, 6):
        if tuple(subset) in context.historical_subsets_6:
            return 6

    for subset in itertools.combinations(numbers, 5):
        if tuple(subset) in context.historical_subsets_5:
            return 5

    for subset in itertools.combinations(numbers, 4):
        if tuple(subset) in context.historical_subsets_4:
            return 4

    return 0


def calculate_combination_metrics(
    numbers: NumberTuple,
    config: AppConfig,
    historical_context: HistoricalContext,
    *,
    include_historical_overlap: bool = True,
) -> CombinationMetrics:
    """Spočítá metriky potřebné pro filtry a scoring.

    Pokud ``include_historical_overlap`` nastavíme na False, přeskočí se dražší
    výpočet historické podobnosti. To se hodí pro první průchod levnými filtry.
    """
    filter_cfg = config.filters
    gen = config.generator

    if not numbers:
        raise ValueError("Nelze spočítat metriky pro prázdnou kombinaci.")
    if len(numbers) != gen.pick_count:
        raise ValueError(
            f"Kombinace musí mít přesně {gen.pick_count} čísel, nalezeno {len(numbers)}."
        )
    if len(set(numbers)) != len(numbers):
        raise ValueError("Kombinace musí obsahovat unikátní čísla.")
    if any(number < gen.number_min or number > gen.number_max for number in numbers):
        raise ValueError(
            f"Kombinace obsahuje číslo mimo rozsah {gen.number_min}–{gen.number_max}."
        )

    total_sum = sum(numbers)
    odd_count = sum(1 for number in numbers if number % 2 == 1)
    even_count = len(numbers) - odd_count

    low_count = count_range(numbers, filter_cfg.low_range)
    high_count = len(numbers) - low_count

    tier_counts = count_ranges(numbers, filter_cfg.tier_ranges)
    bucket_counts = count_ranges(numbers, filter_cfg.bucket_ranges)

    non_empty_tiers = sum(1 for count in tier_counts if count > 0)
    non_empty_buckets = sum(1 for count in bucket_counts if count > 0)
    max_bucket_count = max(bucket_counts) if bucket_counts else 0

    span = numbers[-1] - numbers[0]
    gaps = tuple(b - a for a, b in zip(numbers, numbers[1:], strict=False))
    max_gap = max(gaps) if gaps else 0
    gap_std = population_std(gaps)

    digit_counts = Counter(number % 10 for number in numbers)
    max_same_last_digit = max(digit_counts.values()) if digit_counts else 0

    number_set = frozenset(numbers)
    repeated_from_last_draw = len(number_set & historical_context.last_draw_numbers)
    neighbors_of_last_draw = len(number_set & historical_context.last_draw_neighbors)

    return CombinationMetrics(
        numbers=numbers,
        total_sum=total_sum,
        odd_count=odd_count,
        even_count=even_count,
        low_count=low_count,
        high_count=high_count,
        tier_counts=tier_counts,
        bucket_counts=bucket_counts,
        non_empty_tiers=non_empty_tiers,
        non_empty_buckets=non_empty_buckets,
        max_bucket_count=max_bucket_count,
        span=span,
        gaps=gaps,
        max_gap=max_gap,
        gap_std=gap_std,
        adjacent_pairs=adjacent_pair_count(numbers),
        max_consecutive_run_length=max_consecutive_run_length(numbers),
        max_same_last_digit=max_same_last_digit,
        max_historical_overlap=(
            max_historical_overlap(numbers, historical_context)
            if include_historical_overlap
            else 0
        ),
        repeated_from_last_draw=repeated_from_last_draw,
        neighbors_of_last_draw=neighbors_of_last_draw,
    )



def add_historical_overlap(
    metrics: CombinationMetrics,
    historical_context: HistoricalContext,
) -> CombinationMetrics:
    """Doplní do již vypočtených metrik pouze historický překryv.

    Ostatní metriky zůstávají beze změny, takže se po strukturálních filtrech
    nemusí počítat podruhé.
    """
    return replace(
        metrics,
        max_historical_overlap=max_historical_overlap(metrics.numbers, historical_context),
    )

def historical_number_frequencies(context: HistoricalContext) -> Counter[int]:
    """Četnosti čísel v validních historických datech."""
    counter: Counter[int] = Counter()
    for draw in context.valid_draws:
        counter.update(draw.numbers)
    return counter


def historical_sum_distribution(context: HistoricalContext) -> Counter[int]:
    """Rozložení součtů validních historických tahů."""
    return Counter(sum(draw.numbers) for draw in context.valid_draws)


def historical_odd_even_distribution(context: HistoricalContext) -> Counter[tuple[int, int]]:
    """Rozložení poměru lichá/sudá ve validních historických tazích."""
    distribution: Counter[tuple[int, int]] = Counter()
    for draw in context.valid_draws:
        odd_count = sum(1 for number in draw.numbers if number % 2 == 1)
        distribution[(odd_count, len(draw.numbers) - odd_count)] += 1
    return distribution


def historical_span_distribution(context: HistoricalContext) -> Counter[int]:
    """Rozložení rozpětí ve validních historických tazích."""
    return Counter(draw.numbers[-1] - draw.numbers[0] for draw in context.valid_draws)
