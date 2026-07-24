from extra_renta.web_app.vault_state import (
    CLOSED,
    ERROR,
    GENERATING,
    OPEN,
    VAULT_MESSAGE_KEY,
    VAULT_STATE_KEY,
    initialise_vault,
    reset_vault_for_configuration,
    set_vault_state,
)


def test_vault_state_transitions_and_result_independent_storage() -> None:
    session: dict[str, object] = {"last_result": {"kept": True}}
    snapshot = initialise_vault(session)
    assert snapshot.state == CLOSED

    assert set_vault_state(session, GENERATING, "Počítám").state == GENERATING
    assert set_vault_state(session, OPEN, "Hotovo").state == OPEN
    assert set_vault_state(session, ERROR, "Chyba").state == ERROR
    assert session["last_result"] == {"kept": True}


def test_configuration_change_closes_vault_but_preserves_previous_result() -> None:
    session: dict[str, object] = {"last_result": "previous"}
    initialise_vault(session)
    first = {"preset_key": "recommended", "seed": 42}
    changed = {"preset_key": "strict", "seed": 42}

    assert reset_vault_for_configuration(session, first) is False
    set_vault_state(session, OPEN, "Hotovo")
    assert reset_vault_for_configuration(session, changed) is True
    assert session[VAULT_STATE_KEY] == CLOSED
    assert "Nastavení se změnilo" in str(session[VAULT_MESSAGE_KEY])
    assert session["last_result"] == "previous"


def test_invalid_persisted_state_is_repaired() -> None:
    session: dict[str, object] = {VAULT_STATE_KEY: "unknown"}
    snapshot = initialise_vault(session)
    assert snapshot.state == CLOSED
