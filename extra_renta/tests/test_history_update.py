from pathlib import Path

from extra_renta.core.statistics import build_historical_context
from extra_renta.history_update.models import FetchedDraw
from extra_renta.history_update.parser import parse_draws_from_text
from extra_renta.history_update.service import (
    apply_history_update,
    build_history_update_preview,
    check_new_draws_against_run,
    format_historical_draws_py,
)
from extra_renta.presets import get_preset


def test_parse_draws_from_json_script():
    html = '''
    <html><body>
    <script type="application/json">
    {"draws": [{"date": "2026-07-09", "numbers": [2, 8, 14, 19, 23, 27, 31]}]}
    </script>
    </body></html>
    '''

    draws = parse_draws_from_text(html, source="test")

    assert draws == (FetchedDraw(date="2026-07-09", numbers=(2, 8, 14, 19, 23, 27, 31), source="test"),)


def test_parse_draws_from_czech_text_window():
    text = "Losování 9. 7. 2026: vylosovaná čísla 2 8 14 19 23 27 31"

    draws = parse_draws_from_text(text, source="test")

    assert draws[0].date == "2026-07-09"
    assert draws[0].numbers == (2, 8, 14, 19, 23, 27, 31)


def test_history_update_preview_finds_new_existing_and_conflict():
    current = [
        {"date": "2026-07-01", "numbers": [1, 2, 3, 4, 5, 6, 7]},
        {"date": "2026-07-02", "numbers": [2, 3, 4, 5, 6, 7, 8]},
    ]
    fetched = [
        FetchedDraw(date="2026-07-01", numbers=(1, 2, 3, 4, 5, 6, 7)),
        FetchedDraw(date="2026-07-02", numbers=(3, 4, 5, 6, 7, 8, 9)),
        FetchedDraw(date="2026-07-03", numbers=(4, 5, 6, 7, 8, 9, 10)),
    ]

    preview = build_history_update_preview(fetched, current_draws=current, source_url="test")

    assert len(preview.existing_draws) == 1
    assert len(preview.conflicting_draws) == 1
    assert len(preview.new_draws) == 1


def test_apply_history_update_writes_backup_and_merged_file(tmp_path):
    target = tmp_path / "historical_draws.py"
    target.write_text('HISTORICAL_DRAWS = [{"date": "2026-07-01", "numbers": [1, 2, 3, 4, 5, 6, 7]}]\n', encoding="utf-8")
    preview = build_history_update_preview(
        [FetchedDraw(date="2026-07-02", numbers=(2, 3, 4, 5, 6, 7, 8))],
        current_draws=[{"date": "2026-07-01", "numbers": [1, 2, 3, 4, 5, 6, 7]}],
        source_url="test",
    )

    result = apply_history_update(preview, target_path=target)

    assert result.updated
    assert result.backup_path is not None
    assert Path(result.backup_path).exists()
    content = target.read_text(encoding="utf-8")
    assert '"date": "2026-07-02"' in content


def test_format_historical_draws_py_contains_disclaimer():
    content = format_historical_draws_py([{"date": "2026-07-02", "numbers": [2, 3, 4, 5, 6, 7, 8]}])

    assert "ne pro predikci výhry" in content
    assert "HISTORICAL_DRAWS" in content


def test_check_new_draws_against_run_reuses_combination_check():
    preset = get_preset("recommended")
    config = preset.config
    context = build_historical_context([], config)
    candidate_pool = []
    selected = []
    draw = FetchedDraw(date="2026-07-09", numbers=(6, 9, 12, 14, 23, 25, 30))

    results = check_new_draws_against_run(
        [draw],
        config=config,
        historical_context=context,
        candidate_pool=candidate_pool,
        selected=selected,
    )

    assert len(results) == 1
    assert results[0][0] == draw
    assert results[0][1].numbers == draw.numbers


def test_fetch_history_update_preview_accepts_injected_fetcher_for_history_check():
    from extra_renta.history_update.service import fetch_history_update_preview

    preview = fetch_history_update_preview(
        fetcher=lambda: (FetchedDraw(date="2099-01-01", numbers=(6, 9, 12, 14, 23, 25, 30)),),
        source_url="mock://history-check",
    )

    assert preview.source_error is None
    assert len(preview.fetched_draws) == 1
    assert len(preview.new_draws) == 1
    assert preview.new_draws[0].date == "2099-01-01"


def test_parse_draws_from_public_archive_czech_text_date():
    html = """
    <h2>Archiv</h2>
    Čtvrtek  9. července, 2026
    48 000 000 Kč
    Tažená čísla
    10
    14
    17
    21
    27
    29
    32
    8
    Pondělí  6. července, 2026
    48 000 000 Kč
    Tažená čísla
    4
    14
    16
    23
    24
    25
    33
    26
    """

    draws = parse_draws_from_text(html, source="archive")

    assert draws[0] == FetchedDraw(date="2026-07-06", numbers=(4, 14, 16, 23, 24, 25, 33), source="archive")
    assert draws[1] == FetchedDraw(date="2026-07-09", numbers=(10, 14, 17, 21, 27, 29, 32), source="archive")


def test_fetch_available_history_draws_uses_fallback_when_primary_has_no_draws(monkeypatch):
    from extra_renta.history_update import fetcher as fetcher_module

    pages = {
        "official": "<html><h3>Aktuální výsledky</h3><p>Načítáme slosování…</p></html>",
        "archive": "Pondělí  6. července, 2026 Tažená čísla 4 14 16 23 24 25 33 26",
    }

    def fake_fetch_text_from_url(url: str, *, timeout: int = 20) -> str:
        return pages[url]

    monkeypatch.setattr(fetcher_module, "fetch_text_from_url", fake_fetch_text_from_url)

    draws = fetcher_module.fetch_available_history_draws(urls=("official", "archive"))

    assert draws == (FetchedDraw(date="2026-07-06", numbers=(4, 14, 16, 23, 24, 25, 33), source="archive"),)


def test_fetch_history_update_preview_reports_actual_fallback_source(monkeypatch):
    from extra_renta.history_update import service as service_module

    def fake_fetch_available_history_draws():
        return (FetchedDraw(date="2099-01-01", numbers=(6, 9, 12, 14, 23, 25, 30), source="archive"),)

    monkeypatch.setattr(service_module, "fetch_available_history_draws", fake_fetch_available_history_draws)

    preview = service_module.fetch_history_update_preview()

    assert preview.source_url == "archive"
    assert preview.source_error is None
    assert len(preview.new_draws) == 1
