from extra_renta.history_update.source_names import source_page_name
from extra_renta.web_app.service import WebRunOptions, normalize_web_options


def test_history_source_is_shown_as_page_name_only() -> None:
    assert source_page_name("https://www.allwyn.cz/loterie/extra-renta/kontrola-a-vysledky") == "Allwyn – Extra Renta"
    assert source_page_name("https://vyhraj.cz/loterie/extra-renta/archiv-vysledku/") == "Vyhraj.cz – archiv Extra Renty"


def test_hidden_output_limit_uses_preset_default() -> None:
    normalized = normalize_web_options(WebRunOptions(preset_key="recommended"))

    assert normalized.max_output_count is not None
    assert normalized.max_output_count > 0
