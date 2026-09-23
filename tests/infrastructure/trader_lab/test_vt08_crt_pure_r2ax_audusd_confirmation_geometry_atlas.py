from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ax_audusd_confirmation_geometry_atlas import (
    ARM,
    END,
    IDENTITY,
    MARKET,
    MIN_BUCKET_TRADES,
    MIN_SUPPORTED_YEARS,
    START,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2ax_identity_and_market_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AX_AUDUSD_CONFIRMATION_GEOMETRY_ATLAS_001"
    assert MARKET is CrtPureMarket.AUDUSD
    assert ARM is TargetArm.FIXED_1_5R


def test_r2ax_window_and_support_are_frozen() -> None:
    assert START.year == 2016
    assert END.year == 2026
    assert MIN_BUCKET_TRADES == 60
    assert MIN_SUPPORTED_YEARS == 6
