from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bl_usdjpy_pf_root_cause import (
    END,
    IDENTITY,
    MARKET,
    START,
    YEARS,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2bl_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BL_USDJPY_PF_ROOT_CAUSE_001"
    assert MARKET is CrtPureMarket.USDJPY
    assert START.year == 2014
    assert END.year == 2026
    assert YEARS == 12
