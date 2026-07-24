"""Výchozí konfigurace projektu Extra Renta.

Skutečné předvolby jsou centralizované v modulu ``presets.py``. Tento modul
ponechává zpětně kompatibilní konstantu DEFAULT_CONFIG pro testy a starší kód.
"""

from __future__ import annotations

from .presets import DEFAULT_PRESET_KEY, get_preset

DEFAULT_CONFIG = get_preset(DEFAULT_PRESET_KEY).config
