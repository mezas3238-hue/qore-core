from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2am_high_retention_ablation import (
    CONFIGS,
    END,
    IDENTITY,
    MIN_RETENTION,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2am_identity_and_retention_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AM_HIGH_RETENTION_ABLATION_001"
    assert MIN_RETENTION == 0.60


def test_r2am_long_windows_match_density_research() -> None:
    assert CONFIGS[CrtPureMarket.AUDUSD].start.year == 2016
    assert CONFIGS[CrtPureMarket.USDJPY].start.year == 2014
    assert END.year == 2026
