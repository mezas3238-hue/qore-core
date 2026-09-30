from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as lab,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)


def test_consensus_compresses_on_two_adverse_votes() -> None:
    assert lab._risk_multiplier(
        policy="ADAPTIVE_CONSENSUS",
        state=governor.StabilityState.WATCH,
        adverse_votes=2,
        severe_votes=0,
    ) == Decimal("0.65")


def test_severe_defensive_compresses_more() -> None:
    assert lab._risk_multiplier(
        policy="ADAPTIVE_CONSENSUS",
        state=governor.StabilityState.DEFENSIVE,
        adverse_votes=3,
        severe_votes=2,
    ) == Decimal("0.35")


def test_no_adverse_votes_keeps_full_risk() -> None:
    assert lab._risk_multiplier(
        policy="ADAPTIVE_CONSERVATIVE",
        state=governor.StabilityState.DEFENSIVE,
        adverse_votes=0,
        severe_votes=0,
    ) == Decimal("1")
