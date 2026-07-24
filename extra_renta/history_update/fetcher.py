"""Stažení výsledků Extra Renty z externích zdrojů.

Primární zdroj je oficiální stránka Allwyn/Sazka. Protože tato stránka může
výsledky načítat dynamicky přes JavaScript a v běžně staženém HTML nemusí
obsahovat samotná čísla, aktualizace umí použít i veřejný HTML archiv jako
záložní zdroj. Každý tah si nese informaci o URL zdroje, ze kterého byl skutečně
naparsován.
"""

from __future__ import annotations

import gzip
import zlib
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import FetchedDraw
from .parser import parse_draws_from_text

OFFICIAL_EXTRA_RENTA_RESULTS_URL = "https://www.allwyn.cz/loterie/extra-renta/kontrola-a-vysledky"
OFFICIAL_EXTRA_RENTA_RESULTS_URL_NO_WWW = "https://allwyn.cz/loterie/extra-renta/kontrola-a-vysledky"
SAZKA_EXTRA_RENTA_RESULTS_URL = "https://www.sazka.cz/loterie/extra-renta/kontrola-a-vysledky"
PUBLIC_EXTRA_RENTA_ARCHIVE_URL = "https://vyhraj.cz/loterie/extra-renta/archiv-vysledku/"
PUBLIC_EXTRA_RENTA_ARCHIVE_WWW_URL = "https://www.vyhraj.cz/loterie/extra-renta/archiv-vysledku/"
PUBLIC_EXTRA_RENTA_DETAIL_URL = "https://vyhraj.cz/loterie/extra-renta/"
PUBLIC_EXTRA_RENTA_DETAIL_WWW_URL = "https://www.vyhraj.cz/loterie/extra-renta/"
DEFAULT_HISTORY_SOURCE_URLS = (
    OFFICIAL_EXTRA_RENTA_RESULTS_URL,
    OFFICIAL_EXTRA_RENTA_RESULTS_URL_NO_WWW,
    SAZKA_EXTRA_RENTA_RESULTS_URL,
    PUBLIC_EXTRA_RENTA_ARCHIVE_URL,
    PUBLIC_EXTRA_RENTA_ARCHIVE_WWW_URL,
    PUBLIC_EXTRA_RENTA_DETAIL_URL,
    PUBLIC_EXTRA_RENTA_DETAIL_WWW_URL,
)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


class HistoryFetchError(RuntimeError):
    """Chyba při získávání výsledků z externího zdroje."""


@dataclass(frozen=True)
class HistoryFetchResult:
    """Výsledek stažení z prvního úspěšného zdroje včetně diagnostiky."""

    draws: tuple[FetchedDraw, ...]
    source_url: str
    errors: tuple[str, ...]


@dataclass(frozen=True)
class _FetchCandidate:
    text: str
    final_url: str


def _decode_response(payload: bytes, *, charset: str, content_encoding: str) -> str:
    encoding = content_encoding.lower().strip()
    raw_payload = payload
    if "gzip" in encoding:
        raw_payload = gzip.decompress(payload)
    elif "deflate" in encoding:
        raw_payload = zlib.decompress(payload)
    return raw_payload.decode(charset or "utf-8", errors="replace")


def fetch_text_from_url(url: str, *, timeout: int = 20) -> str:
    """Stáhne text z URL pomocí standardní knihovny."""
    request = Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
            # Nechceme brotli, protože standardní knihovna jej neumí spolehlivě dekomprimovat.
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "close",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL je řízený zdroj dat.
            charset = response.headers.get_content_charset() or "utf-8"
            content_encoding = response.headers.get("Content-Encoding", "")
            return _decode_response(response.read(), charset=charset, content_encoding=content_encoding)
    except (HTTPError, URLError, TimeoutError, OSError, zlib.error) as exc:
        raise HistoryFetchError(f"Nepodařilo se stáhnout výsledky ze zdroje {url}: {exc}") from exc


def fetch_draws_from_url(url: str, *, timeout: int = 20) -> tuple[FetchedDraw, ...]:
    """Stáhne a naparsuje tahy z jedné konkrétní URL."""
    text = fetch_text_from_url(url, timeout=timeout)
    draws = parse_draws_from_text(text, source=url)
    if not draws:
        snippet = " ".join(text[:500].replace("\n", " ").split())
        raise HistoryFetchError(
            f"Zdroj {url} byl stažen, ale nepodařilo se v něm najít žádné tahy. "
            "Web může výsledky načítat dynamicky nebo změnil strukturu stránky. "
            f"Ukázka obsahu: {snippet[:240]}"
        )
    return draws


def fetch_available_history_result(
    *,
    urls: Iterable[str] = DEFAULT_HISTORY_SOURCE_URLS,
    timeout: int = 20,
) -> HistoryFetchResult:
    """Vrátí tahy z prvního dostupného zdroje, který obsahuje parsovatelná data."""
    errors: list[str] = []
    for url in urls:
        try:
            draws = fetch_draws_from_url(url, timeout=timeout)
        except HistoryFetchError as exc:
            errors.append(str(exc))
            continue
        actual_source = draws[0].source if draws else url
        return HistoryFetchResult(draws=draws, source_url=actual_source, errors=tuple(errors))

    joined_errors = "\n- " + "\n- ".join(errors) if errors else "nebyl zadán žádný zdroj"
    raise HistoryFetchError(f"Nepodařilo se získat tahy z žádného dostupného zdroje. Detaily:{joined_errors}")


def fetch_available_history_draws(
    *,
    urls: Iterable[str] = DEFAULT_HISTORY_SOURCE_URLS,
    timeout: int = 20,
) -> tuple[FetchedDraw, ...]:
    """Zpětně kompatibilní wrapper vracející pouze tahy."""
    return fetch_available_history_result(urls=urls, timeout=timeout).draws


def fetch_official_draws(*, url: str = OFFICIAL_EXTRA_RENTA_RESULTS_URL, timeout: int = 20) -> tuple[FetchedDraw, ...]:
    """Stáhne a naparsuje tahy pouze z oficiálního webu Allwyn."""
    return fetch_draws_from_url(url, timeout=timeout)
