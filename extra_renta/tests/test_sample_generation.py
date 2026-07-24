from extra_renta.config import DEFAULT_CONFIG
from extra_renta.core.combination_generator import generate_random_combinations


def test_sample_combinations_are_unique_and_reproducible():
    first = list(generate_random_combinations(DEFAULT_CONFIG.generator, 100, seed=123))
    second = list(generate_random_combinations(DEFAULT_CONFIG.generator, 100, seed=123))

    assert first == second
    assert len(first) == 100
    assert len(set(first)) == 100
    assert all(tuple(sorted(numbers)) == numbers for numbers in first)
    assert all(len(numbers) == DEFAULT_CONFIG.generator.pick_count for numbers in first)
