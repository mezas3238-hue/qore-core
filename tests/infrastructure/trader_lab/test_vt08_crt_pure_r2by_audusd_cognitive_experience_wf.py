from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2by_audusd_cognitive_experience_wf as r2by,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2by_contract_is_frozen() -> None:
    assert r2by.IDENTITY == (
        "VT08_CRT_PURE_R2BY_AUDUSD_COGNITIVE_EXPERIENCE_WF_001"
    )
    assert r2by.MARKET is CrtPureMarket.AUDUSD
    assert r2by.MIN_CELL_SUPPORT == 30
    assert r2by.PRIOR_STRENGTH == 100.0
