"""Reserved 1Y holdout contract for Capitalizer V49.

This is NOT the protected Fresh Holdout 2014-09-17 -> 2016-09-17.
The V49 reserved holdout is a separate one-year slice from retained provider-native M1:

    2024-09-17T00:00Z -> 2025-09-17T00:00Z

V49 development/capacity work uses:
    2025-09-17T00:00Z -> 2026-09-17T00:00Z

The two windows do not overlap. The holdout is opened once to count deterministic V49
trade intents. Its result must not be used to mutate V49 and then rerun the same window
as if it remained holdout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

IDENTITY = "QORE_CAPITALIZER_V49_RESERVED_HOLDOUT_1Y"
HOLDOUT_START = datetime(2024, 9, 17, tzinfo=UTC)
HOLDOUT_END = datetime(2025, 9, 17, tzinfo=UTC)
DEVELOPMENT_START = datetime(2025, 9, 17, tzinfo=UTC)
DEVELOPMENT_END = datetime(2026, 9, 17, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class V49ReservedHoldoutContract:
    identity: str = IDENTITY
    holdout_start: datetime = HOLDOUT_START
    holdout_end: datetime = HOLDOUT_END
    development_start: datetime = DEVELOPMENT_START
    development_end: datetime = DEVELOPMENT_END
    fresh_holdout_used: bool = False
    holdout_purpose: str = "COUNT_DETERMINISTIC_TRADE_INTENTS"
    methodology_mutation_after_result_allowed: bool = False
    second_pass_same_holdout_after_mutation_allowed: bool = False
    economics_required_for_this_test: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V49 reserved holdout identity is frozen")
        if self.holdout_end <= self.holdout_start:
            raise ValueError("holdout window must be positive")
        if self.development_end <= self.development_start:
            raise ValueError("development window must be positive")
        if self.holdout_end > self.development_start:
            raise ValueError("V49 holdout and development windows cannot overlap")
        if self.fresh_holdout_used:
            raise ValueError("protected Fresh Holdout must remain sealed")
        if self.methodology_mutation_after_result_allowed:
            raise ValueError("holdout result cannot authorize methodology mutation")
        if self.second_pass_same_holdout_after_mutation_allowed:
            raise ValueError("mutated V49 cannot reuse the same reserved holdout")
        if self.economics_required_for_this_test:
            raise ValueError("this holdout answers trade-count capacity only")
        if self.live_authorized or self.real_capital_authorized:
            raise ValueError("holdout contract grants no deployment authority")


V49_RESERVED_HOLDOUT_1Y = V49ReservedHoldoutContract()
