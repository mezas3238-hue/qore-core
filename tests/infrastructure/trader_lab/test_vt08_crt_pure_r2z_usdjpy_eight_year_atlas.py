from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2z_usdjpy_eight_year_atlas import (
    BLOCK_2,
    BLOCK_3,
    BLOCK_4,
    END,
    IDENTITY,
    MARKET,
    START,
    _windows,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2z_identity_and_market_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2Z_USDJPY_EIGHT_YEAR_ATLAS_001"
    assert MARKET is CrtPureMarket.USDJPY


def test_r2z_windows_are_four_ordered_two_year_blocks() -> None:
    assert START < BLOCK_2 < BLOCK_3 < BLOCK_4 < END
    assert (BLOCK_2 - START).days >= 700
    assert (BLOCK_3 - BLOCK_2).days >= 700
    assert (BLOCK_4 - BLOCK_3).days >= 700
    assert (END - BLOCK_4).days >= 700


def test_r2z_empty_report_keeps_all_blocks() -> None:
    report = _windows(())
    assert tuple(report) == (
        "full_8y",
        "block_2018_20",
        "block_2020_22",
        "block_2022_24",
        "block_2024_26",
    )
    assert all(int(summary["trades"]) == 0 for summary in report.values())
