"""Source-native TTrades continuation observation for Capitalizer V48.

A continuation is not a naked FVG touch. Reviewed TTrades continuation material requires
price to reach a source-valid continuation POI (for example an FVG or swept high/low)
and then confirm with a closure through the opposing candle series (CISD).

This module classifies a pre-economic continuation opportunity only. It does not choose an
entry price, target, position size, route ranking, outcome or capital allocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48StructuralCISDObservation,
)

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_CONTINUATION"


class V48ContinuationPOIKind(StrEnum):
    FAIR_VALUE_GAP = "FAIR_VALUE_GAP"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"


@dataclass(frozen=True, slots=True)
class V48ContinuationObservation:
    identity: str
    direction: CapitalizerSourceDirection
    higher_timeframe_direction: CapitalizerSourceDirection
    poi_kind: V48ContinuationPOIKind
    poi_reached: bool
    cisd_source_valid: bool
    confirmed: bool
    outcome_used: bool = False
    entry_price_selected: bool = False
    target_selected: bool = False
    execution_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 continuation identity is frozen")
        expected = (
            self.poi_reached
            and self.cisd_source_valid
            and self.direction is self.higher_timeframe_direction
        )
        if self.confirmed != expected:
            raise ValueError("continuation status/payload mismatch")
        if self.outcome_used or self.entry_price_selected or self.target_selected:
            raise ValueError("continuation observation must remain pre-economic")
        if self.execution_authority or self.capital_authority:
            raise ValueError("continuation observation grants no execution/capital authority")


def assess_source_native_continuation(
    *,
    direction: CapitalizerSourceDirection,
    higher_timeframe_direction: CapitalizerSourceDirection,
    poi_kind: V48ContinuationPOIKind,
    poi_reached: bool,
    cisd: V48StructuralCISDObservation,
) -> V48ContinuationObservation:
    """Require POI reach + source-valid CISD aligned with the route thesis."""

    cisd_valid = cisd.source_valid and cisd.direction is direction
    confirmed = (
        poi_reached
        and cisd_valid
        and direction is higher_timeframe_direction
    )
    return V48ContinuationObservation(
        identity=IDENTITY,
        direction=direction,
        higher_timeframe_direction=higher_timeframe_direction,
        poi_kind=poi_kind,
        poi_reached=poi_reached,
        cisd_source_valid=cisd_valid,
        confirmed=confirmed,
    )
