"""Mechanical source-faithful higher-timeframe bias for QORE Capitalizer V2.

The selected Capitalizer route does not attempt to encode every possible ICT/TTrades bias method.
It freezes one explicit, source-supported mechanical path:
higher-timeframe Candle 2 or Candle 3 closure at a valid point of interest establishes direction;
lower timeframes may confirm/execute but cannot create the narrative.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
)


class CapitalizerDailyBiasResolution(StrEnum):
    CONFIRMED = "CONFIRMED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class CapitalizerDailyBiasObservation:
    resolution: CapitalizerDailyBiasResolution
    direction: CapitalizerSourceDirection | None
    reasons: tuple[str, ...]
    source_route: str = "HTF_C2_C3_CLOSURE_AT_POI"
    lower_timeframe_created_bias: bool = False
    numeric_indicator_used: bool = False
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.lower_timeframe_created_bias:
            raise ValueError("lower timeframe cannot create Capitalizer higher-timeframe bias")
        if self.numeric_indicator_used:
            raise ValueError("source daily bias route cannot use invented numeric indicator")
        if self.grants_entry_authority:
            raise ValueError("daily bias does not grant entry authority")
        if self.grants_capital_authority:
            raise ValueError("daily bias does not grant capital authority")
        if self.resolution is CapitalizerDailyBiasResolution.CONFIRMED:
            if self.direction is None:
                raise ValueError("confirmed daily bias requires direction")
        elif self.direction is not None:
            raise ValueError("unresolved daily bias cannot carry direction")


def derive_daily_bias(
    closure: CapitalizerSourceClosureObservation | None,
) -> CapitalizerDailyBiasObservation:
    """Resolve direction only from a valid source closure at POI."""

    if closure is None or not closure.source_rule_satisfied:
        return CapitalizerDailyBiasObservation(
            resolution=CapitalizerDailyBiasResolution.UNRESOLVED,
            direction=None,
            reasons=("HTF_C2_C3_CLOSURE_AT_POI_NOT_CONFIRMED",),
        )

    return CapitalizerDailyBiasObservation(
        resolution=CapitalizerDailyBiasResolution.CONFIRMED,
        direction=closure.direction,
        reasons=(
            "HTF_C2_C3_CLOSURE_AT_POI_CONFIRMED",
            f"DIRECTION:{closure.direction.value}",
        ),
    )
