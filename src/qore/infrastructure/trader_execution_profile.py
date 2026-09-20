"""Frozen runtime execution profiles by decision timeframe.

These profiles are transport/runtime contracts. They do not modify trader
methodology, signal logic, entry, stop, target or certified risk.

M1 traders:
- decision/order-send deadline: 5.0 seconds
- broker tick maximum age: 2.0 seconds

M5 traders:
- decision/order-send deadline: 10.0 seconds
- broker tick maximum age: 2.0 seconds

Fresh-tick enforcement remains independent from the wider decision window.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TraderExecutionProfile:
    timeframe: str
    decision_deadline_seconds: Decimal
    tick_max_age_seconds: Decimal
    normal_feed_refresh_seconds: Decimal
    boundary_arm_lead_seconds: Decimal
    boundary_retry_ms: int

    @property
    def decision_deadline(self) -> timedelta:
        return timedelta(seconds=float(self.decision_deadline_seconds))

    @property
    def tick_max_age(self) -> timedelta:
        return timedelta(seconds=float(self.tick_max_age_seconds))


M1_PROFILE = TraderExecutionProfile(
    timeframe="M1",
    decision_deadline_seconds=Decimal("5.0"),
    tick_max_age_seconds=Decimal("2.0"),
    normal_feed_refresh_seconds=Decimal("1.0"),
    boundary_arm_lead_seconds=Decimal("10.0"),
    boundary_retry_ms=75,
)

M5_PROFILE = TraderExecutionProfile(
    timeframe="M5",
    decision_deadline_seconds=Decimal("10.0"),
    tick_max_age_seconds=Decimal("2.0"),
    normal_feed_refresh_seconds=Decimal("1.0"),
    boundary_arm_lead_seconds=Decimal("10.0"),
    boundary_retry_ms=75,
)

PROFILES = {
    "M1": M1_PROFILE,
    "M5": M5_PROFILE,
}


def profile_for_timeframe(timeframe: str) -> TraderExecutionProfile:
    try:
        return PROFILES[timeframe]
    except KeyError as error:
        raise ValueError(f"unsupported trader execution timeframe={timeframe}") from error
