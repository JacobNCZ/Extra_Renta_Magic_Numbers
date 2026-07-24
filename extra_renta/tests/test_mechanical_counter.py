from extra_renta.web_app.mechanical_counter import build_counter_html
from extra_renta.web_app.vault_state import CLOSED, GENERATING, OPEN


def test_mechanical_counter_idle_uses_seven_empty_reels() -> None:
    html = build_counter_html(CLOSED, "Připraveno")

    assert html.count('class="mc-reel') == 7
    assert "PŘIPRAVENO" in html
    assert "—" in html


def test_mechanical_counter_generating_contains_spin_animation() -> None:
    html = build_counter_html(GENERATING, "Počítám")

    assert html.count("is-spinning") == 7
    assert "@keyframes mcSpin" in html
    assert "GENEROVÁNÍ KOMBINACÍ" in html


def test_mechanical_counter_open_shows_final_combination() -> None:
    html = build_counter_html(
        OPEN,
        "Hotovo",
        final_numbers=(3, 8, 12, 17, 21, 27, 32),
        result_count=100,
    )

    for number in (3, 8, 12, 17, 21, 27, 32):
        assert f">{number:02d}<" in html
    assert "100 vybraných kombinací" in html
    assert html.count("is-final\"") == 7
