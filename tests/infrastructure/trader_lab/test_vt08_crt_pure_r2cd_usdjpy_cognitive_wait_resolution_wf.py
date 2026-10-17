from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cd_usdjpy_cognitive_wait_resolution_wf as r2cd,
)


def test_r2cd_contract_is_frozen() -> None:
    assert r2cd.IDENTITY == (
        "VT08_CRT_PURE_R2CD_USDJPY_COGNITIVE_WAIT_RESOLUTION_WF_001"
    )
    assert str(r2cd.TARGET_R) == "1.5"
    assert r2cd.MIN_CELL_SUPPORT == 30
    assert r2cd.PRIOR_STRENGTH == 100.0
