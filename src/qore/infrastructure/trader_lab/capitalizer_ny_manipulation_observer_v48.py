"""Source-native New York manipulation observer for Capitalizer V48.

Reviewed TTrades profile:
London context/range exists
-> New York sweeps the London range high or low
-> price closes through the opposing candle series (CISD)
-> only then is the directional manipulation profile confirmed.

The observer is pre-economic. It does not choose FVG/OB entry price, stop, target, size,
portfolio priority or outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_CAPITALIZER_V48_NY_MANIPULATION_OBSERVER"


class V48NYSweptSide(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class V48NYManipulationState(StrEnum):
    CONFIRMED = "CONFIRMED"
    WAIT = "WAIT"


@dataclass(frozen=True, slots=True)
class V48NYManipulationObservation:
    identity: str
    state: V48NYManipulationState
    london_context_resolved: bool
    swept_side: V48NYSweptSide | None
    direction: CapitalizerSourceDirection | None
    sweep_at: datetime | None
    swept_level: Decimal | None
    sweep_extreme: Decimal | None
    causal_series_open: Decimal | None
    cisd_confirmed_at: datetime | None
    cisd_confirmation_close: Decimal | None
    outcome_used: bool = False
    entry_model_selected: bool = False
    target_selected: bool = False
    execution_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("NY manipulation observer identity is frozen")
        payload = (
            self.swept_side,
            self.direction,
            self.sweep_at,
            self.swept_level,
            self.sweep_extreme,
            self.causal_series_open,
            self.cisd_confirmed_at,
            self.cisd_confirmation_close,
        )
        payload_complete = all(value is not None for value in payload)
        confirmed = self.state is V48NYManipulationState.CONFIRMED
        if confirmed != (self.london_context_resolved and payload_complete):
            raise ValueError("NY manipulation state/payload mismatch")
        if self.outcome_used or self.entry_model_selected or self.target_selected:
            raise ValueError("NY manipulation observation must remain pre-economic")
        if self.execution_authority or self.capital_authority:
            raise ValueError("NY manipulation observation grants no execution/capital authority")


def _opposing(bar: CapitalizerM1Bar, direction: CapitalizerSourceDirection) -> bool:
    if direction is CapitalizerSourceDirection.BULLISH:
        return bar.close < bar.open
    return bar.close > bar.open


def _series_boundary(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    sweep_index: int,
    direction: CapitalizerSourceDirection,
) -> Decimal | None:
    end = sweep_index if _opposing(bars[sweep_index], direction) else sweep_index - 1
    if end < 0 or not _opposing(bars[end], direction):
        return None
    start = end
    while start > 0 and _opposing(bars[start - 1], direction):
        start -= 1
    return bars[start].open


def observe_new_york_manipulation(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    london_range_high: Decimal,
    london_range_low: Decimal,
    london_context_resolved: bool,
) -> V48NYManipulationObservation:
    """Return the first London-range sweep followed by a confirming CISD."""

    if london_range_low <= 0 or london_range_high <= 0:
        raise ValueError("London range levels must be positive")
    if london_range_low >= london_range_high:
        raise ValueError("London range low must be below high")

    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    if ordered != bars:
        raise ValueError("NY manipulation bars must be chronological")

    if not london_context_resolved:
        return V48NYManipulationObservation(
            identity=IDENTITY,
            state=V48NYManipulationState.WAIT,
            london_context_resolved=False,
            swept_side=None,
            direction=None,
            sweep_at=None,
            swept_level=None,
            sweep_extreme=None,
            causal_series_open=None,
            cisd_confirmed_at=None,
            cisd_confirmation_close=None,
        )

    for index, bar in enumerate(bars):
        bullish_sweep = bar.low < london_range_low and bar.close > london_range_low
        bearish_sweep = bar.high > london_range_high and bar.close < london_range_high
        if bullish_sweep == bearish_sweep:
            continue

        direction = (
            CapitalizerSourceDirection.BULLISH
            if bullish_sweep
            else CapitalizerSourceDirection.BEARISH
        )
        swept_side = V48NYSweptSide.LOW if bullish_sweep else V48NYSweptSide.HIGH
        level = london_range_low if bullish_sweep else london_range_high
        extreme = bar.low if bullish_sweep else bar.high
        boundary = _series_boundary(bars, sweep_index=index, direction=direction)
        if boundary is None:
            continue

        for candidate in bars[index + 1 :]:
            crossed = (
                candidate.close > boundary
                if direction is CapitalizerSourceDirection.BULLISH
                else candidate.close < boundary
            )
            if not crossed:
                continue
            return V48NYManipulationObservation(
                identity=IDENTITY,
                state=V48NYManipulationState.CONFIRMED,
                london_context_resolved=True,
                swept_side=swept_side,
                direction=direction,
                sweep_at=bar.closed_at,
                swept_level=level,
                sweep_extreme=extreme,
                causal_series_open=boundary,
                cisd_confirmed_at=candidate.closed_at,
                cisd_confirmation_close=candidate.close,
            )

    return V48NYManipulationObservation(
        identity=IDENTITY,
        state=V48NYManipulationState.WAIT,
        london_context_resolved=True,
        swept_side=None,
        direction=None,
        sweep_at=None,
        swept_level=None,
        sweep_extreme=None,
        causal_series_open=None,
        cisd_confirmed_at=None,
        cisd_confirmation_close=None,
    )
