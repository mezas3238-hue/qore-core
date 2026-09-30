from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)
from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_risk_compression_2r_v1 as lab,
)


def test_defensive_lt1_is_compressed() -> None:
    assert lab._multiplier(
        policy="DEF_LT1_035",
        state=governor.StabilityState.DEFENSIVE,
        destination="LT_1R",
    ) == Decimal("0.35")


def test_stable_trade_keeps_full_risk() -> None:
    assert lab._multiplier(
        policy="CAUSAL_RECOVERY_LADDER",
        state=governor.StabilityState.STABLE,
        destination="LT_1R",
    ) == Decimal("1")


def test_watch_low_room_uses_intermediate_risk() -> None:
    assert lab._multiplier(
        policy="CAUSAL_RECOVERY_LADDER",
        state=governor.StabilityState.WATCH,
        destination="LT_1R",
    ) == Decimal("0.75")
