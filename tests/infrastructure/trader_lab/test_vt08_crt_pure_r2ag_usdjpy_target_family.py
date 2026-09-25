from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    ARMS,
    TARGET_MULTIPLE,
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ag_usdjpy_target_family import (
    EFF5_HIGH,
    EFF5_LOW,
    MARKET,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2ag_reuses_exact_target_family() -> None:
    assert ARMS == (
        TargetArm.MIDPOINT_CONTROL,
        TargetArm.FIXED_1R,
        TargetArm.FIXED_1_5R,
        TargetArm.FIXED_2R,
    )
    assert TARGET_MULTIPLE[TargetArm.FIXED_1_5R] == Decimal("1.5")


def test_r2ag_keeps_exact_usdjpy_regime() -> None:
    assert MARKET is CrtPureMarket.USDJPY
    assert EFF5_LOW == Decimal("0.10")
    assert EFF5_HIGH == Decimal("0.20")
