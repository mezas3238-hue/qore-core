from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bc_usdjpy_confirmation_geometry_atlas import (
    END,
    IDENTITY,
    MARKET,
    MIN_BUCKET_TRADES,
    MIN_SUPPORTED_YEARS,
    START,
    YEARS,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2bc_is_independent_usdjpy_atlas() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BC_USDJPY_CONFIRMATION_GEOMETRY_ATLAS_001"
    assert MARKET is CrtPureMarket.USDJPY
    assert START.year == 2014
    assert END.year == 2026
    assert YEARS == 12


def test_r2bc_support_floor_is_frozen() -> None:
    assert MIN_BUCKET_TRADES == 72
    assert MIN_SUPPORTED_YEARS == 7
