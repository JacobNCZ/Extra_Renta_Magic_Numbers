"""Parser externích výsledků Extra Renty.

Parser je záměrně tolerantní. Oficiální web může část obsahu vkládat přes
JavaScript, veřejné archivy zase používají běžný HTML text. Proto podporujeme:

* JSON-like bloky ve skriptech,
* textové bloky ve formátu ``datum → Tažená čísla → čísla``,
* obecné textové okno za nalezeným datem jako poslední fallback.

Pokud se struktura webu změní, parser bezpečně vrátí prázdný seznam místo pádu
programu.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from .models import FetchedDraw

ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
CZ_DATE_RE = re.compile(r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d{2})\b")
CZ_TEXT_DATE_RE = re.compile(
    r"\b(?:pond[eě]l[ií]|[úu]ter[yý]|st[řr]eda|[čc]tvrtek|p[aá]tek|sobota|ned[eě]le)?\s*"
    r"(\d{1,2})\.\s*([A-Za-zÁ-ž]+),?\s*(20\d{2})\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"(?<!\d)(?:[1-9]|[12]\d|3[0-3])(?!\d)")
SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
DRAW_NUMBERS_MARKER_RE = re.compile(
    r"(?:ta[zž]en[aá]\s+[čc]ísla|vylosovan[aá]\s+[čc]ísla|v[yý]hern[ií]\s+[čc]ísla)",
    re.IGNORECASE,
)

DATE_KEYS = {"date", "drawDate", "draw_date", "datum", "drawDateIso", "drawnAt", "drawn_at"}
NUMBER_KEYS = {"numbers", "drawNumbers", "draw_numbers", "cisla", "winningNumbers", "winning_numbers"}

_CZECH_MONTHS = {
    "leden": 1,
    "ledna": 1,
    "unor": 2,
    "unora": 2,
    "brezen": 3,
    "brezna": 3,
    "duben": 4,
    "dubna": 4,
    "kveten": 5,
    "kvetna": 5,
    "cerven": 6,
    "cervna": 6,
    "cervenec": 7,
    "cervence": 7,
    "srpen": 8,
    "srpna": 8,
    "zari": 9,
    "rijen": 10,
    "rijna": 10,
    "listopad": 11,
    "listopadu": 11,
    "prosinec": 12,
    "prosince": 12,
}


def _normalize_token(value: str) -> str:
    """Vrátí text bez diakritiky a malými písmeny."""
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _clean_html_text(text: str) -> str:
    """Převede HTML na čitelný text se zachovanými mezerami mezi položkami."""
    without_scripts = SCRIPT_RE.sub(" ", text)
    without_styles = STYLE_RE.sub(" ", without_scripts)
    with_spaces = re.sub(r"<(?:br|p|div|li|tr|td|th|h\d|span)[^>]*>", " ", without_styles, flags=re.IGNORECASE)
    plain = html.unescape(TAG_RE.sub(" ", with_spaces))
    plain = plain.replace("\xa0", " ")
    return re.sub(r"\s+", " ", plain).strip()


def normalize_date(raw_value: object) -> str | None:
    """Převede datum v ISO, českém číselném nebo českém textovém formátu na ``YYYY-MM-DD``."""
    value = str(raw_value).strip()
    iso_match = ISO_DATE_RE.search(value)
    if iso_match:
        year, month, day = iso_match.groups()
        try:
            return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            return None

    cz_match = CZ_DATE_RE.search(value)
    if cz_match:
        day, month, year = cz_match.groups()
        try:
            return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            return None

    text_match = CZ_TEXT_DATE_RE.search(value)
    if text_match:
        day, month_name, year = text_match.groups()
        month = _CZECH_MONTHS.get(_normalize_token(month_name))
        if month is None:
            return None
        try:
            return datetime(int(year), month, int(day)).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def normalize_numbers(raw_value: object) -> tuple[int, ...] | None:
    """Převede externí reprezentaci čísel na seřazenou sedmici 1–33."""
    if isinstance(raw_value, str):
        parts: Iterable[object] = NUMBER_RE.findall(raw_value)
    elif isinstance(raw_value, Iterable):
        parts = raw_value
    else:
        return None

    numbers: list[int] = []
    for value in parts:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 33:
            numbers.append(number)

    if len(numbers) < 7:
        return None
    first_seven = tuple(sorted(numbers[:7]))
    if len(first_seven) != 7 or len(set(first_seven)) != 7:
        return None
    return first_seven


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _extract_from_json_value(value: Any, *, source: str) -> list[FetchedDraw]:
    draws: list[FetchedDraw] = []
    for item in _walk_json(value):
        date_value = None
        number_value = None
        for key, candidate in item.items():
            normalized_key = str(key).strip()
            if normalized_key in DATE_KEYS and date_value is None:
                date_value = candidate
            if normalized_key in NUMBER_KEYS and number_value is None:
                number_value = candidate
        date = normalize_date(date_value) if date_value is not None else None
        numbers = normalize_numbers(number_value) if number_value is not None else None
        if date and numbers:
            draws.append(FetchedDraw(date=date, numbers=numbers, source=source))
    return draws


def _parse_json_blocks(text: str, *, source: str) -> list[FetchedDraw]:
    draws: list[FetchedDraw] = []
    for match in SCRIPT_RE.finditer(text):
        payload = html.unescape(match.group(1)).strip()
        if not payload or not payload.startswith(("{", "[")):
            continue
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            continue
        draws.extend(_extract_from_json_value(value, source=source))
    return draws


def _date_matches(text: str) -> tuple[re.Match[str], ...]:
    matches = [*ISO_DATE_RE.finditer(text), *CZ_DATE_RE.finditer(text), *CZ_TEXT_DATE_RE.finditer(text)]
    # Více regexů může v některých textech trefit překrývající se datum.
    matches.sort(key=lambda item: (item.start(), -(item.end() - item.start())))
    unique: list[re.Match[str]] = []
    last_end = -1
    for match in matches:
        if match.start() < last_end:
            continue
        unique.append(match)
        last_end = match.end()
    return tuple(unique)


def _numbers_after_marker(block: str) -> tuple[int, ...] | None:
    marker = DRAW_NUMBERS_MARKER_RE.search(block)
    if not marker:
        return None
    return normalize_numbers(NUMBER_RE.findall(block[marker.end() :]))


def _parse_draw_blocks(clean_text: str, *, source: str) -> list[FetchedDraw]:
    """Parsuje nejspolehlivější textový tvar: datum → Tažená čísla → čísla."""
    draws: list[FetchedDraw] = []
    matches = _date_matches(clean_text)
    for index, date_match in enumerate(matches):
        date = normalize_date(date_match.group(0))
        if not date:
            continue
        block_end = matches[index + 1].start() if index + 1 < len(matches) else min(len(clean_text), date_match.end() + 900)
        block = clean_text[date_match.end() : block_end]
        numbers = _numbers_after_marker(block)
        if numbers:
            draws.append(FetchedDraw(date=date, numbers=numbers, source=source))
    return draws


def _parse_text_windows(clean_text: str, *, source: str) -> list[FetchedDraw]:
    """Obecný fallback pro jednoduché texty typu ``datum: čísla``."""
    draws: list[FetchedDraw] = []
    for date_match in _date_matches(clean_text):
        date = normalize_date(date_match.group(0))
        if not date:
            continue
        window = clean_text[date_match.end() : date_match.end() + 360]
        numbers = normalize_numbers(NUMBER_RE.findall(window))
        if numbers:
            draws.append(FetchedDraw(date=date, numbers=numbers, source=source))
    return draws


def deduplicate_draws(draws: Iterable[FetchedDraw]) -> tuple[FetchedDraw, ...]:
    """Odstraní duplicitní záznamy podle data a kombinace."""
    seen: set[tuple[str, tuple[int, ...]]] = set()
    unique: list[FetchedDraw] = []
    for draw in draws:
        key = (draw.date, draw.numbers)
        if key in seen:
            continue
        seen.add(key)
        unique.append(draw)
    return tuple(sorted(unique, key=lambda item: item.date))


def parse_draws_from_text(text: str, *, source: str = "official") -> tuple[FetchedDraw, ...]:
    """Vrátí nalezené tahy z HTML/JSON/textu externího zdroje."""
    clean_text = _clean_html_text(text)
    draws = [
        *_parse_json_blocks(text, source=source),
        *_parse_draw_blocks(clean_text, source=source),
        *_parse_text_windows(clean_text, source=source),
    ]
    return deduplicate_draws(draws)
