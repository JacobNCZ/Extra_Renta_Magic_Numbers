"""Uživatelské názvy externích stránek s historickými tahy."""

from __future__ import annotations

from urllib.parse import urlparse


def source_page_name(source: str) -> str:
    """Vrátí uživatelsky čitelný název stránky bez URL a technických detailů."""
    host = urlparse(source).netloc.lower().removeprefix("www.")
    if host == "allwyn.cz":
        return "Allwyn – Extra Renta"
    if host == "sazka.cz":
        return "Sazka – Extra Renta"
    if host == "vyhraj.cz":
        return "Vyhraj.cz – archiv Extra Renty"
    if source.startswith("mock://"):
        return "Testovací zdroj"
    return host or "Externí stránka"
