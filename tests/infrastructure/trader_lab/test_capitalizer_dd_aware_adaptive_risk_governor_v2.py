from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)
from qore.infrastructure.trader_lab import (
    capitalizer_dd_aware_adaptive_risk_governor_v2 as lab,
)


def test_ceiling_hardens_above_five_and_half_r() -> None:
    assert lab._multiplier(
        policy="EDGE_DD_CEILING",
        state=governor.StabilityState.DEFENSIVE,
        current_dd=Decimal("5.5"),
        adverse_votes=0,
        severe_votes=0,
    ) == Decimal("0.10")


def test_balanced_keeps_full_risk_without_pressure() -> None:
    assert lab._multiplier(
        policy="EDGE_DD_BALANCED",
        state=governor.StabilityState.STABLE,
        current_dd=Decimal("1"),
        adverse_votes=0,
        severe_votes=0,
    ) == Decimal("1")


def test_asymmetric_compresses_confirmed_severe_edge() -> None:
    assert lab._multiplier(
        policy="EDGE_DD_ASYMMETRIC",
        state=governor.StabilityState.DEFENSIVE,
        current_dd=Decimal("3.5"),
        adverse_votes=3,
        severe_votes=2,
    ) == Decimal("0.20")
