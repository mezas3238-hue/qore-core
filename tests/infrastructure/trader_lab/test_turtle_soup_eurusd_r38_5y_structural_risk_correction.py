from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r38_5y_structural_risk_correction as r38,
)


def test_r38_acceptance_is_not_relaxed() -> None:
    assert r38.MIN_TRADES == 800
    assert r38.MIN_PF_010 == Decimal("1.50")
    assert r38.MAX_DD_010 == Decimal("6.0")


def test_r38_only_adds_preentry_risk_overlays() -> None:
    assert r38.F5_SHORT_OVERLAY_SCALE == Decimal("0.10")
    assert r38.UNSTABLE_LONG_ROUTE_OVERLAY_SCALE == Decimal("0.50")
    assert r38.FAMILY_SET == "R36_F235_FROZEN"
    assert r38.GOVERNOR == "FRAGILITY_050_025_010"
