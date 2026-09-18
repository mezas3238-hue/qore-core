from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r38_structural_fragility_risk_correction as r38,
)


def test_r38_owner_gate_is_fixed() -> None:
    assert r38.MIN_TRADES == 350
    assert r38.MIN_PF_010 == Decimal("1.90")
    assert r38.MAX_DD_010 == Decimal("6.0")
    assert set(r38.ENSEMBLES) == {"R38_FROZEN_SIGNAL_BASELINE"}


def test_r38_fragility_overlay_is_nonzero_and_preentry() -> None:
    assert r38.FRAGILITY_FLAGS == (
        "M5_EFFICIENCY_MEDIUM",
        "D1_RANGE_EXPANDED",
        "PROJECTED_R_Q2_LE_1",
    )
    assert r38.FRAGILITY_POLICY == (
        Decimal("1"),
        Decimal("0.20"),
        Decimal("0.05"),
        Decimal("0.01"),
    )
    assert min(r38.FRAGILITY_POLICY) > Decimal("0")


def test_r38_base_confidence_policy_is_predeclared() -> None:
    assert r38.RISK_POLICIES == {
        "AUDJPY_CONFIDENCE_100_075_025": (
            Decimal("1"),
            Decimal("0.75"),
            Decimal("0.25"),
        )
    }
