"""Source-faithful point-of-interest detection for QORE Capitalizer V2.

Supported baseline POIs come directly from reviewed TTrades mechanics:
- Fair Value Gap: three-candle non-overlap (internal liquidity);
- Swing High / Swing Low: external liquidity with lower highs or higher lows on both sides.

No statistical level, fitted threshold, or post-outcome information is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)


class CapitalizerSourcePOIKind(StrEnum):
    BULLISH_FVG = "BULLISH_FVG"
    BEARISH_FVG = "BEARISH_FVG"
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"


@dataclass(frozen=True, slots=True)
class CapitalizerSourcePOI:
    kind: CapitalizerSourcePOIKind
    lower_price: Decimal
    upper_price: Decimal
    source_bar_count: int
    confirmed: bool = True
    source_equivalent: bool = True

    def __post_init__(self) -> None:
        if self.lower_price > self.upper_price:
            raise ValueError("POI lower price cannot exceed upper price")
        if self.source_bar_count != 3:
            raise ValueError("baseline source POI requires three bars")
        if not self.confirmed or not self.source_equivalent:
            raise ValueError("stored Capitalizer source POI must be confirmed/source-equivalent")


def detect_fair_value_gap(
    *,
    candle1: CapitalizerSourceBar,
    candle2: CapitalizerSourceBar,
    candle3: CapitalizerSourceBar,
) -> CapitalizerSourcePOI | None:
    """Detect TTrades three-candle FVG using wick non-overlap."""

    del candle2  # middle candle participates in the formation but defines no gap boundary.
    if candle1.high < candle3.low:
        return CapitalizerSourcePOI(
            kind=CapitalizerSourcePOIKind.BULLISH_FVG,
            lower_price=candle1.high,
            upper_price=candle3.low,
            source_bar_count=3,
        )
    if candle1.low > candle3.high:
        return CapitalizerSourcePOI(
            kind=CapitalizerSourcePOIKind.BEARISH_FVG,
            lower_price=candle3.high,
            upper_price=candle1.low,
            source_bar_count=3,
        )
    return None


def detect_external_liquidity_swing(
    *,
    left: CapitalizerSourceBar,
    center: CapitalizerSourceBar,
    right: CapitalizerSourceBar,
) -> CapitalizerSourcePOI | None:
    """Detect source-defined swing high/low external liquidity."""

    swing_high = center.high > left.high and center.high > right.high
    swing_low = center.low < left.low and center.low < right.low
    if swing_high and swing_low:
        return None
    if swing_high:
        return CapitalizerSourcePOI(
            kind=CapitalizerSourcePOIKind.SWING_HIGH,
            lower_price=center.high,
            upper_price=center.high,
            source_bar_count=3,
        )
    if swing_low:
        return CapitalizerSourcePOI(
            kind=CapitalizerSourcePOIKind.SWING_LOW,
            lower_price=center.low,
            upper_price=center.low,
            source_bar_count=3,
        )
    return None


def bar_interacts_with_poi(
    *,
    bar: CapitalizerSourceBar,
    poi: CapitalizerSourcePOI,
) -> bool:
    """Return whether a completed bar traded into/through a causal POI."""

    return bar.high >= poi.lower_price and bar.low <= poi.upper_price


def any_source_poi_interaction(
    *,
    bar: CapitalizerSourceBar,
    pois: tuple[CapitalizerSourcePOI, ...],
) -> bool:
    return any(bar_interacts_with_poi(bar=bar, poi=poi) for poi in pois)
