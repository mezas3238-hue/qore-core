from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bz_usdjpy_cognitive_experience_wf as r2bz,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2bz_contract_is_frozen() -> None:
    assert r2bz.IDENTITY == (
        "VT08_CRT_PURE_R2BZ_USDJPY_COGNITIVE_EXPERIENCE_WF_001"
    )
    assert r2bz.MARKET is CrtPureMarket.USDJPY
    assert r2bz.MIN_CELL_SUPPORT == 30
    assert r2bz.PRIOR_STRENGTH == 100.0
