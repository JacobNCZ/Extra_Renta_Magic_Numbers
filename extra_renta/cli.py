"""CLI a interaktivní průvodce pro Extra Renta."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from .output.exporter import load_last_run_config
from .pipeline import DEFAULT_DRY_RUN_SAMPLE_SIZE, DEFAULT_SAMPLE_SIZE, FULL_MODE, SAMPLE_MODE
from .presets import DEFAULT_PRESET_KEY, PRESETS, PresetConfig, format_preset_detail, format_preset_menu, get_preset

MAIN_ACTION_GENERATE = "generate"
MAIN_ACTION_UPDATE_HISTORY = "update-history"
MAIN_ACTION_EXIT = "exit"
HISTORY_UPDATE_CHECK_AVAILABLE = "check-available"
HISTORY_UPDATE_CHECK_RULES = "check-rules"
HISTORY_UPDATE_APPLY = "apply"
HISTORY_UPDATE_BACK = "back"


def format_main_menu() -> str:
    return "\n".join([
        "=== EXTRA RENTA ===",
        "",
        "1. Spustit generátor kandidátních kombinací",
        "2. Aktualizovat historické tahy",
        "",
        "0. Konec",
    ])


def choose_main_action() -> str:
    actions = {"1": MAIN_ACTION_GENERATE, "2": MAIN_ACTION_UPDATE_HISTORY, "0": MAIN_ACTION_EXIT}
    while True:
        print(format_main_menu())
        try:
            choice = input("\nZadej číslo volby [0-2], Enter = 1: ").strip() or "1"
        except EOFError:
            return MAIN_ACTION_GENERATE
        if choice in actions:
            return actions[choice]
        print("Neplatná volba.\n")


def format_history_update_menu() -> str:
    return "\n".join([
        "=== AKTUALIZACE HISTORICKÝCH DAT ===",
        "",
        "1. Pouze zkontrolovat dostupné nové tahy",
        "2. Zkontrolovat nové tahy proti filtrům a scoringu",
        "3. Aktualizovat historická data",
        "",
        "0. Zpět",
    ])


def choose_history_update_action() -> str:
    actions = {"1": HISTORY_UPDATE_CHECK_AVAILABLE, "2": HISTORY_UPDATE_CHECK_RULES, "3": HISTORY_UPDATE_APPLY, "0": HISTORY_UPDATE_BACK}
    while True:
        print(format_history_update_menu())
        try:
            choice = input("\nZadej číslo volby [0-3]: ").strip()
        except EOFError:
            return HISTORY_UPDATE_BACK
        if choice in actions:
            return actions[choice]
        print("Neplatná volba.\n")


def ask_text(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def ask_optional_int(prompt: str, *, default: int) -> int:
    while True:
        try:
            raw = input(f"{prompt} [Enter = {default:,}]: ".replace(",", " ")).strip()
        except EOFError:
            return default
        if not raw:
            return default
        try:
            value = int(raw.replace(" ", ""))
        except ValueError:
            print("Zadej celé číslo.\n")
            continue
        if value > 0:
            return value
        print("Hodnota musí být větší než nula.\n")


def _ask_yes_no(prompt: str, *, default: bool = False) -> bool:
    default_label = "a" if default else "n"
    while True:
        try:
            value = input(f"{prompt} [a/n, Enter = {default_label}]: ").strip().lower()
        except EOFError:
            return default
        if not value:
            return default
        if value in {"a", "ano", "y", "yes"}:
            return True
        if value in {"n", "ne", "no"}:
            return False


@dataclass(frozen=True)
class RunOptions:
    preset: PresetConfig
    generation_mode: str = FULL_MODE
    sample_size: int = DEFAULT_SAMPLE_SIZE
    seed: int | None = 42


RUN_MODE_DETAILS: tuple[tuple[str, str, str], ...] = (
    (FULL_MODE, "Kompletní běh", "Projede všech 4 272 048 kombinací a finální portfolio vybere MMR."),
    (SAMPLE_MODE, "Diagnostický vzorek", "Rychle otestuje pravidla na náhodném vzorku; není určen jako finální výstup."),
)


def choose_preset() -> PresetConfig:
    presets = list(PRESETS.values())
    while True:
        print(format_preset_menu())
        try:
            raw = input(f"\nZadej číslo předvolby [1-{len(presets)}], Enter = 1: ").strip()
        except EOFError:
            return get_preset(DEFAULT_PRESET_KEY)
        index = 1 if not raw else int(raw) if raw.isdigit() else 0
        if 1 <= index <= len(presets):
            preset = presets[index - 1]
            print("\n" + format_preset_detail(preset) + "\n")
            if _ask_yes_no("Použít tuto předvolbu?", default=True):
                return preset
        else:
            print("Neplatná volba.\n")


def format_run_mode_menu() -> str:
    lines = ["=== REŽIM BĚHU ==="]
    for index, (_, label, description) in enumerate(RUN_MODE_DETAILS, start=1):
        lines.extend((f"{index}. {label}", f"   {description}"))
    return "\n".join(lines)


def choose_run_mode() -> str:
    print(format_run_mode_menu())
    try:
        raw = input("\nZadej číslo režimu [1-2], Enter = 1: ").strip()
    except EOFError:
        return FULL_MODE
    return SAMPLE_MODE if raw == "2" else FULL_MODE


def maybe_use_last_run_options() -> RunOptions | None:
    payload = load_last_run_config("output/last_run_config.json")
    if not payload or str(payload.get("preset_key", "")) not in PRESETS:
        return None
    mode = str(payload.get("generation_mode", FULL_MODE))
    if mode not in {FULL_MODE, SAMPLE_MODE}:
        mode = FULL_MODE
    return RunOptions(
        preset=get_preset(str(payload["preset_key"])),
        generation_mode=mode,
        sample_size=int(payload.get("sample_size", DEFAULT_SAMPLE_SIZE) or DEFAULT_SAMPLE_SIZE),
        seed=payload.get("seed") if isinstance(payload.get("seed"), int) else 42,
    )


def choose_interactive_run_options(*, allow_last_config: bool = True) -> RunOptions:
    if allow_last_config:
        last = maybe_use_last_run_options()
        if last and _ask_yes_no("Použít poslední uložené nastavení?", default=False):
            return last
    preset = choose_preset()
    mode = choose_run_mode()
    sample_size = DEFAULT_SAMPLE_SIZE
    seed: int | None = 42
    if mode == SAMPLE_MODE:
        sample_size = ask_optional_int("Velikost diagnostického vzorku", default=DEFAULT_DRY_RUN_SAMPLE_SIZE)
        seed = ask_optional_int("Seed vzorkování", default=42)
    return RunOptions(preset=preset, generation_mode=mode, sample_size=sample_size, seed=seed)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extra Renta – generátor kandidátních kombinací")
    parser.add_argument("--preset", choices=tuple(PRESETS), default=DEFAULT_PRESET_KEY)
    parser.add_argument("--mode", choices=(FULL_MODE, SAMPLE_MODE), default=FULL_MODE)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-export", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check-combination")
    parser.add_argument("--interactive", action="store_true")
    return parser.parse_args(argv)


def argv_or_sys(argv: list[str] | None) -> list[str]:
    return list(sys.argv[1:] if argv is None else argv)
