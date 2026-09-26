"""Causal liquidity-take observation for source-faithful Failure to Manipulate."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerLiquiditySideTaken,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    CapitalizerSourcePOIKind,
)


@dataclass(frozen=True, slots=True)
class CapitalizerLiquidityReference:
    side: CapitalizerLiquiditySideTaken
    price: Decimal
    poi_kind: CapitalizerSourcePOIKind

    def __post_init__(self) -> None:
        if not isinstance(self.price, Decimal) or not self.price.is_finite():
            raise ValueError("liquidity reference price must be finite Decimal")
        if self.poi_kind not in {
            CapitalizerSourcePOIKind.SWING_HIGH,
            CapitalizerSourcePOIKind.SWING_LOW,
        }:
            raise ValueError("baseline FTM liquidity reference requires external swing liquidity")


def liquidity_reference_from_poi(
    poi: CapitalizerSourcePOI,
) -> CapitalizerLiquidityReference:
    if poi.kind is CapitalizerSourcePOIKind.SWING_HIGH:
        return CapitalizerLiquidityReference(
            side=CapitalizerLiquiditySideTaken.HIGH,
            price=poi.upper_price,
            poi_kind=poi.kind,
        )
    if poi.kind is CapitalizerSourcePOIKind.SWING_LOW:
        return CapitalizerLiquidityReference(
            side=CapitalizerLiquiditySideTaken.LOW,
            price=poi.lower_price,
            poi_kind=poi.kind,
        )
    raise ValueError("FTM baseline requires swing-high or swing-low external liquidity POI")


@dataclass(frozen=True, slots=True)
class CapitalizerLiquidityTakeObservation:
    side: CapitalizerLiquiditySideTaken
    reference_price: Decimal
    observed_extreme: Decimal
    level_taken: bool
    closed_bar_observed: bool = True
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value in (self.reference_price, self.observed_extreme):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError("liquidity-take prices must be finite Decimal values")
        if not self.closed_bar_observed:
            raise ValueError("liquidity-take observation requires a completed bar")
        if not self.reasons:
            raise ValueError("liquidity-take observation requires reasons")


def detect_liquidity_take(
    *,
    reference_side: CapitalizerLiquiditySideTaken,
    reference_price: Decimal,
    closed_bar: CapitalizerSourceBar,
) -> CapitalizerLiquidityTakeObservation:
    """Detect a strict take beyond a known high/low using a completed causal bar."""

    if not isinstance(reference_price, Decimal) or not reference_price.is_finite():
        raise ValueError("liquidity reference must be finite Decimal")

    if reference_side is CapitalizerLiquiditySideTaken.HIGH:
        extreme = closed_bar.high
        taken = extreme > reference_price
    else:
        extreme = closed_bar.low
        taken = extreme < reference_price

    return CapitalizerLiquidityTakeObservation(
        side=reference_side,
        reference_price=reference_price,
        observed_extreme=extreme,
        level_taken=taken,
        reasons=(
            f"REFERENCE_SIDE:{reference_side.value}",
            "LIQUIDITY_LEVEL_TAKEN" if taken else "LIQUIDITY_LEVEL_NOT_TAKEN",
            "CLOSED_BAR_OBSERVED",
        ),
    )
