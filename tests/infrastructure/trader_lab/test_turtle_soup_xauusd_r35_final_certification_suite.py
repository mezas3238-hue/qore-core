from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r35_final_certification_suite as r35,
)


def test_r35_gate_contract_is_frozen() -> None:
    assert r35.WFO_BLOCKS == 10
    assert r35.WFO_MIN_POSITIVE_BLOCKS == 6
    assert r35.WFO_MIN_AGGREGATE_PF == Decimal("1.30")
    assert r35.MC_PATHS == 20_000
    assert r35.MC_BLOCK_SIZE == 5
    assert r35.MC_SEED == 20260918
    assert r35.MC_MIN_POSITIVE_TERMINAL_PROB == Decimal("0.99")
    assert r35.MC_MAX_P95_DD_R == Decimal("20.0")
    assert r35.MC_MAX_P99_DD_R == Decimal("25.0")


def test_r35_stress_and_slippage_are_predeclared() -> None:
    assert set(r35.STRESS_SCENARIOS) == {
        "EXTRA_002",
        "EXTRA_005",
        "EXTRA_010",
    }
    assert set(r35.SLIPPAGE_SCENARIOS) == {
        "NORMAL",
        "ADVERSE",
        "SEVERE",
    }
    assert r35.STRESS_SCENARIOS["EXTRA_010"]["extra_r"] == Decimal("0.10")
    assert r35.SLIPPAGE_SCENARIOS["SEVERE"]["STOP"] == Decimal("0.100")


def test_r35_robustness_is_fail_closed() -> None:
    assert r35.ROBUST_MIN_POSITIVE_ANNUAL_BLOCKS == 4
    assert r35.ROBUST_MIN_POSITIVE_HALF_YEAR_BLOCKS == 6
    assert r35.ROBUST_MIN_SOURCE_PF == Decimal("1.30")
    assert r35.ROBUST_MIN_POSITIVE_FAMILIES == 4
    assert r35.ROBUST_MIN_LOYO_PF == Decimal("1.30")
