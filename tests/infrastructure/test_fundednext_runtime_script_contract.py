from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME = _ROOT / "scripts" / "qore_fundednext_runtime.py"


def test_h4_exit_comment_uses_broker_verified_29_character_limit() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    expected = '"comment": f"qore-h4-exit-{str(position.ticket)}"[:29],'
    assert expected in source
    assert '"comment": f"qore-h4-exit-{str(position.ticket)}"[:31],' not in source
