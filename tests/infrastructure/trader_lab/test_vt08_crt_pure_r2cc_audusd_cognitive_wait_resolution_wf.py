from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cc_audusd_cognitive_wait_resolution_wf as r2cc,
)


def test_r2cc_contract_is_frozen() -> None:
    assert r2cc.IDENTITY == (
        "VT08_CRT_PURE_R2CC_AUDUSD_COGNITIVE_WAIT_RESOLUTION_WF_001"
    )
    assert str(r2cc.TARGET_R) == "1.5"
    assert r2cc.MIN_CELL_SUPPORT == 30
    assert r2cc.PRIOR_STRENGTH == 100.0
