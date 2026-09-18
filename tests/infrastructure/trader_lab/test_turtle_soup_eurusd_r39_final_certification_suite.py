from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r39_final_certification_suite as r39,
)


def test_r39_gate_contract_is_frozen() -> None:
    assert r39.WFO_BLOCKS == 10
    assert r39.WFO_MIN_POSITIVE_BLOCKS == 6
    assert r39.WFO_MIN_AGGREGATE_PF == Decimal("1.30")
    assert r39.MC_PATHS == 20_000
    assert r39.MC_BLOCK_SIZE == 5
    assert r39.MC_SEED == 20260918
    assert r39.MC_MIN_POSITIVE_TERMINAL_PROB == Decimal("0.99")
    assert r39.MC_MAX_P95_DD_R == Decimal("20.0")
    assert r39.MC_MAX_P99_DD_R == Decimal("25.0")


def test_r39_stress_and_slippage_are_predeclared() -> None:
    assert set(r39.STRESS_SCENARIOS) == {
        "EXTRA_002",
        "EXTRA_005",
        "EXTRA_010",
    }
    assert set(r39.SLIPPAGE_SCENARIOS) == {
        "NORMAL",
        "ADVERSE",
        "SEVERE",
    }
    assert r39.STRESS_SCENARIOS["EXTRA_010"]["extra_r"] == Decimal("0.10")
    assert r39.SLIPPAGE_SCENARIOS["SEVERE"]["STOP"] == Decimal("0.100")
    assert r39.SLIPPAGE_SCENARIOS["SEVERE"]["TRAIL_STOP"] == Decimal("0.100")
    assert r39.SLIPPAGE_SCENARIOS["SEVERE"]["STOP_FIRST"] == Decimal("0.100")


def test_r39_robustness_is_fail_closed_for_three_eurusd_families() -> None:
    assert r39.ROBUST_MIN_POSITIVE_ANNUAL_BLOCKS == 4
    assert r39.ROBUST_MIN_POSITIVE_HALF_YEAR_BLOCKS == 6
    assert r39.ROBUST_MIN_SOURCE_PF == Decimal("1.30")
    assert r39.ROBUST_MIN_POSITIVE_FAMILIES == 3
    assert r39.ROBUST_MIN_LOYO_PF == Decimal("1.30")


def test_r39_source_bindings_are_exact() -> None:
    assert r39.R38_RUN_ID == 35327677519
    assert r39.R38_ARTIFACT_ID == 10539313228
    assert r39.FREEZE_RUN_ID == 35327938780
    assert r39.FREEZE_ARTIFACT_ID == 10539358304
