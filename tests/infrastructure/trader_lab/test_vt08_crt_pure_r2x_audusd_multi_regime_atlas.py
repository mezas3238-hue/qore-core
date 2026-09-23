from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2x_audusd_multi_regime_atlas import (
    BLOCK_2,
    BLOCK_3,
    END,
    IDENTITY,
    MARKET,
    START,
    _windows,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2x_identity_and_market_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2X_AUDUSD_MULTI_REGIME_ATLAS_001"
    assert MARKET is CrtPureMarket.AUDUSD


def test_r2x_windows_are_ordered_and_non_overlapping() -> None:
    assert START < BLOCK_2 < BLOCK_3 < END
    assert (BLOCK_2 - START).days >= 700
    assert (BLOCK_3 - BLOCK_2).days >= 700
    assert (END - BLOCK_3).days >= 700


def test_r2x_empty_windows_keep_all_frozen_blocks() -> None:
    report = _windows(())

    assert tuple(report) == (
        "full_6y",
        "block_2020_22",
        "block_2022_24",
        "block_2024_26",
    )
    assert all(int(summary["trades"]) == 0 for summary in report.values())
