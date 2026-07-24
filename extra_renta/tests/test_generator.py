from extra_renta.config import DEFAULT_CONFIG
from extra_renta.core.combination_generator import generate_all_combinations, total_combination_count


def test_total_combination_count():
    assert total_combination_count(DEFAULT_CONFIG.generator) == 4_272_048


def test_generator_first_and_unique():
    generator = generate_all_combinations(DEFAULT_CONFIG.generator)
    first = next(generator)
    assert first == (1, 2, 3, 4, 5, 6, 7)
    assert len(first) == len(set(first)) == DEFAULT_CONFIG.generator.pick_count
