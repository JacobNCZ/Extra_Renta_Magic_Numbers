"""Stavový model hlavního generovacího vizuálu bez závislosti na Streamlitu.

Názvy proměnných zůstávají kvůli zpětné kompatibilitě se starší verzí s trezorem.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any

CLOSED = "closed"
GENERATING = "generating"
OPEN = "open"
ERROR = "error"
VALID_STATES = frozenset({CLOSED, GENERATING, OPEN, ERROR})

VAULT_STATE_KEY = "vault_state"
VAULT_MESSAGE_KEY = "vault_message"
VAULT_SIGNATURE_KEY = "vault_options_signature"


@dataclass(frozen=True)
class VaultSnapshot:
    state: str
    message: str


def initialise_vault(session: MutableMapping[str, Any]) -> VaultSnapshot:
    """Doplní bezpečný výchozí stav a vrátí aktuální snapshot."""
    state = session.get(VAULT_STATE_KEY, CLOSED)
    if state not in VALID_STATES:
        state = CLOSED
    session[VAULT_STATE_KEY] = state
    session.setdefault(VAULT_MESSAGE_KEY, "Mechanické počítadlo je připraveno")
    return VaultSnapshot(state=state, message=str(session[VAULT_MESSAGE_KEY]))


def set_vault_state(session: MutableMapping[str, Any], state: str, message: str) -> VaultSnapshot:
    """Nastaví validovaný stav trezoru."""
    if state not in VALID_STATES:
        raise ValueError(f"Neplatný stav trezoru: {state}")
    session[VAULT_STATE_KEY] = state
    session[VAULT_MESSAGE_KEY] = message
    return VaultSnapshot(state=state, message=message)


def reset_vault_for_configuration(
    session: MutableMapping[str, Any], current_signature: dict[str, Any]
) -> bool:
    """Při změně voleb zavře trezor; výsledky ponechá jako historický náhled.

    Vrací True, pokud byla zjištěna změna konfigurace.
    """
    previous = session.get(VAULT_SIGNATURE_KEY)
    session[VAULT_SIGNATURE_KEY] = current_signature
    if previous is None or previous == current_signature:
        return False
    set_vault_state(
        session,
        CLOSED,
        "Nastavení se změnilo. Počítadlo je připravené pro nový běh.",
    )
    return True
