from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bg_audusd_prestop_path_forensics import (
    IDENTITY,
    TRIGGER_R,
)


def test_r2bg_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BG_AUDUSD_PRESTOP_PATH_FORENSICS_001"
    assert str(TRIGGER_R) == "0.75"
