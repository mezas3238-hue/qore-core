from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r45_final_certification_suite as r45,
)


def test_r45_binds_exact_frozen_candidate() -> None:
    assert r45.R43_RUN_ID == 35357443440
    assert r45.R43_ARTIFACT_ID == 10552052483
    assert r45.FREEZE_RUN_ID == 35357779125
    assert r45.FREEZE_ARTIFACT_ID == 10552911323
    assert r45.BASELINE_TRADES == 907
    assert r45.BASELINE_PF == Decimal("1.713624514596208498825398640")
    assert r45.BASELINE_DD == Decimal("4.401231922815307849576052766")
    assert r45.BASELINE_POSITIVE_ANNUAL == 5


def test_r45_requires_all_five_annual_blocks() -> None:
    assert r45.ROBUST_REQUIRED_POSITIVE_ANNUAL_BLOCKS == 5
    assert r45.WFO_BLOCKS == 10
    assert r45.MC_PATHS == 20_000


def test_r45_slippage_supports_runtime_exit_families() -> None:
    normal = r45.SLIPPAGE_SCENARIOS["NORMAL"]
    for reason in (
        "TARGET",
        "STOP",
        "TRAIL_STOP",
        "TRAIL_STOP_FIRST",
        "STOP_FIRST",
        "GAP_STOP",
        "GAP_TRAIL",
        "TIME_24H",
    ):
        assert reason in normal
