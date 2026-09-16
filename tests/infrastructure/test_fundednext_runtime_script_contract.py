from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME = _ROOT / "scripts" / "qore_fundednext_runtime.py"


def test_h4_exit_comment_uses_broker_verified_29_character_limit() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    expected = '"comment": f"qore-h4-exit-{str(position.ticket)}"[:29],'
    assert expected in source
    assert '"comment": f"qore-h4-exit-{str(position.ticket)}"[:31],' not in source


def test_live_activation_adds_rule_freshness_properties_safely() -> None:
    source = (_ROOT / "scripts" / "authorize_fundednext_live.ps1").read_text(
        encoding="utf-8-sig"
    )
    assert "Add-Member -NotePropertyName rules_verified_at" in source
    assert "Add-Member -NotePropertyName rules_valid_until" in source
    assert "$Activation.rules_verified_at =" not in source
    assert "$Activation.rules_valid_until =" not in source
