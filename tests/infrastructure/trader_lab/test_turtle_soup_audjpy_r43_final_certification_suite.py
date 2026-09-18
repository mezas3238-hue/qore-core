from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r43_final_certification_suite as r43,
)


def test_r43_exact_bindings() -> None:
    assert r43.R41_RUN_ID == 35399430491
    assert r43.R41_ARTIFACT_ID == 10569333275
    assert r43.FREEZE_RUN_ID == 35400010014
    assert r43.FREEZE_ARTIFACT_ID == 10569179223


def test_r43_reference_robustness_contract() -> None:
    assert r43.WFO_BLOCK_MONTHS == 6
    assert r43.WFO_BLOCKS == 10
    assert r43.WFO_MIN_POSITIVE_BLOCKS == 6
    assert r43.WFO_MIN_AGGREGATE_PF == Decimal("1.30")
    assert r43.MC_PATHS == 20_000
    assert r43.MC_BLOCK_SIZE == 5
    assert r43.MC_SEED == 20260918
    assert r43.ROBUST_MIN_POSITIVE_ANNUAL_BLOCKS == 5
    assert r43.ROBUST_MIN_LOYO_PF == Decimal("1.30")


def test_r43_stress_and_slippage_are_predeclared() -> None:
    assert set(r43.STRESS_SCENARIOS) == {"EXTRA_002", "EXTRA_005", "EXTRA_010"}
    assert set(r43.SLIPPAGE_SCENARIOS) == {"NORMAL", "ADVERSE", "SEVERE"}
