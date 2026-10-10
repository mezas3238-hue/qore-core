from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)


def test_utility_penalizes_negative_tail() -> None:
    strong = router._utility(
        mean_r=Decimal("0.20"),
        negative_rate=Decimal("0.30"),
        downside=Decimal("0.70"),
    )
    weak = router._utility(
        mean_r=Decimal("0.20"),
        negative_rate=Decimal("0.60"),
        downside=Decimal("1.00"),
    )
    assert strong > weak


def test_defensive_overlay_forces_stage() -> None:
    final_mode, overlay = router._overlay(
        policy="CONTEXT_DEFENSIVE_STAGE",
        base_mode="ORIGINAL",
        state=governor.StabilityState.DEFENSIVE,
    )
    assert overlay is True
    assert final_mode == "STAGED_050_100_150"


def test_context_only_never_overrides() -> None:
    final_mode, overlay = router._overlay(
        policy="CONTEXT_ONLY",
        base_mode="LOCK025_AFTER_075",
        state=governor.StabilityState.DEFENSIVE,
    )
    assert final_mode == "LOCK025_AFTER_075"
    assert overlay is False
