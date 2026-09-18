from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r39_candidate_freeze as r39,
)


def test_r39_freeze_binds_exact_passing_r38() -> None:
    assert r39.SOURCE_RUN_ID == 35396621959
    assert r39.SOURCE_ARTIFACT_ID == 10567832804
    assert r39.SELECTED_ENSEMBLE == "R38_FROZEN_SIGNAL_BASELINE"
    assert r39.SELECTED_POLICY == "AUDJPY_CONFIDENCE_100_075_025"
    assert r39.EXPECTED_TRADES == 422
    assert r39.EXPECTED_PF == "1.914983646549167839637883832"
    assert r39.EXPECTED_DD == "5.04830244641349726210448727"


def test_r39_freeze_preserves_nonzero_fragility_contract() -> None:
    assert r39.EXPECTED_FRAGILITY_FLAGS == (
        "M5_EFFICIENCY_MEDIUM",
        "D1_RANGE_EXPANDED",
        "PROJECTED_R_Q2_LE_1",
    )
    assert r39.EXPECTED_FRAGILITY_POLICY == ("1", "0.20", "0.05", "0.01")
