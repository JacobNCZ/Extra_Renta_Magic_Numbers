"""Generátory kombinací pro Extra Rentu."""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Iterator

from .models import GeneratorConfig, NumberTuple


def validate_generator_config(config: GeneratorConfig) -> None:
    """Zkontroluje základní nastavení generátoru."""
    if config.number_min > config.number_max:
        raise ValueError("number_min nesmí být větší než number_max")

    available_numbers = config.number_max - config.number_min + 1
    if config.pick_count <= 0:
        raise ValueError("pick_count musí být kladné číslo")

    if config.pick_count > available_numbers:
        raise ValueError("pick_count je větší než počet dostupných čísel")


def total_combination_count(config: GeneratorConfig) -> int:
    """Vrátí počet všech možných kombinací bez opakování."""
    validate_generator_config(config)
    available_numbers = config.number_max - config.number_min + 1
    return math.comb(available_numbers, config.pick_count)


def generate_all_combinations(config: GeneratorConfig) -> Iterator[NumberTuple]:
    """Vygeneruje všechny unikátní kombinace pomocí itertools.combinations.

    Pro Extra Rentu jde o C(33, 7) = 4 272 048 kombinací. Funkce je lazy
    generátor, takže nedrží všechny kombinace v paměti najednou.
    """
    validate_generator_config(config)
    yield from itertools.combinations(
        range(config.number_min, config.number_max + 1),
        config.pick_count,
    )


def generate_random_combinations(
    config: GeneratorConfig,
    sample_size: int,
    *,
    seed: int | None = None,
) -> Iterator[NumberTuple]:
    """Vygeneruje reprodukovatelný náhodný diagnostický vzorek.

    Vzorkovaný režim slouží pouze k rychlému testování pravidel.
    Nepředstavuje predikci a nezvyšuje pravděpodobnost výhry.
    """
    validate_generator_config(config)
    if sample_size <= 0:
        raise ValueError("sample_size musí být kladné číslo")

    total = total_combination_count(config)
    if sample_size >= total:
        yield from generate_all_combinations(config)
        return

    rng = random.Random(seed)
    population = tuple(range(config.number_min, config.number_max + 1))
    seen: set[NumberTuple] = set()

    # U menších vzorků vůči C(33, 7) jsou duplicity vzácné. Ochranný limit brání
    # nekonečné smyčce, pokud by někdo nastavil sample_size blízko celému prostoru.
    max_attempts = sample_size * 20
    attempts = 0
    while len(seen) < sample_size and attempts < max_attempts:
        attempts += 1
        numbers = tuple(sorted(rng.sample(population, config.pick_count)))
        if numbers in seen:
            continue
        seen.add(numbers)
        yield numbers

    if len(seen) < sample_size:
        for numbers in generate_all_combinations(config):
            if numbers in seen:
                continue
            seen.add(numbers)
            yield numbers
            if len(seen) >= sample_size:
                break
