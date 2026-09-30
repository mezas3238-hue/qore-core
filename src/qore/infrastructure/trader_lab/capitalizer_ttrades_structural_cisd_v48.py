"""Source-native TTrades CISD/protected-swing primitive for Capitalizer V48.

TTrades source semantics:
higher-timeframe Candle-2/Candle-3 closure first
-> lower-timeframe change in state of delivery
-> the lower-timeframe swing becomes protected
-> only then may the route look for continuation.

This module observes that structural relationship only. It has no outcome, target,
position sizing, session ranking, execution or capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_STRUCTURAL_CISD"


@dataclass(frozen=True, slots=True)
class V48TimedSourceBar:
    opened_at: datetime
    closed_at: datetime
    source: CapitalizerSourceBar

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise ValueError("CISD bar opened_at must be timezone-aware")
        if self.closed_at.tzinfo is None or self.closed_at.utcoffset() is None:
            raise ValueError("CISD bar closed_at must be timezone-aware")
        if self.closed_at <= self.opened_at:
            raise ValueError("CISD bar must close after it opens")


@dataclass(frozen=True, slots=True)
class V48StructuralCISDObservation:
    identity: str
    direction: CapitalizerSourceDirection
    higher_timeframe_closure_confirmed: bool
    swing_occurred_at: datetime | None
    swing_price: Decimal | None
    causal_series_started_at: datetime | None
    causal_series_ended_at: datetime | None
    causal_series_open: Decimal | None
    confirmed_at: datetime | None
    confirmation_close: Decimal | None
    structural_confirmed: bool
    source_valid: bool
    outcome_used: bool = False
    entry_authority: bool = False
    execution_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 structural CISD identity is frozen")
        payload = (
            self.swing_occurred_at,
            self.swing_price,
            self.causal_series_started_at,
            self.causal_series_ended_at,
            self.causal_series_open,
            self.confirmed_at,
            self.confirmation_close,
        )
        payload_complete = all(value is not None for value in payload)
        if self.structural_confirmed != payload_complete:
            raise ValueError("CISD structural status/payload mismatch")
        if self.source_valid != (
            self.structural_confirmed and self.higher_timeframe_closure_confirmed
        ):
            raise ValueError("CISD source-valid status mismatch")
        if self.outcome_used:
            raise ValueError("CISD primitive cannot use terminal outcomes")
        if self.entry_authority or self.execution_authority or self.capital_authority:
            raise ValueError("CISD primitive grants no trading/capital authority")


def _opposing(
    bar: V48TimedSourceBar,
    direction: CapitalizerSourceDirection,
) -> bool:
    if direction is CapitalizerSourceDirection.BULLISH:
        return bar.source.close < bar.source.open
    return bar.source.close > bar.source.open


def _swing_matches(
    left: V48TimedSourceBar,
    center: V48TimedSourceBar,
    right: V48TimedSourceBar,
    direction: CapitalizerSourceDirection,
) -> bool:
    if direction is CapitalizerSourceDirection.BULLISH:
        return (
            center.source.low < left.source.low
            and center.source.low < right.source.low
        )
    return (
        center.source.high > left.source.high
        and center.source.high > right.source.high
    )


def _causal_series(
    bars: tuple[V48TimedSourceBar, ...],
    *,
    center: int,
    direction: CapitalizerSourceDirection,
) -> tuple[V48TimedSourceBar, ...]:
    end = center if _opposing(bars[center], direction) else center - 1
    if end < 0 or not _opposing(bars[end], direction):
        return ()

    start = end
    while start > 0 and _opposing(bars[start - 1], direction):
        start -= 1
    return bars[start : end + 1]


def observe_first_structural_cisd(
    bars: tuple[V48TimedSourceBar, ...],
    *,
    direction: CapitalizerSourceDirection,
    after: datetime,
    before: datetime,
    higher_timeframe_closure_confirmed: bool,
) -> V48StructuralCISDObservation:
    """Observe the first causal LTF swing confirmation in a bounded HTF window."""

    if after.tzinfo is None or after.utcoffset() is None:
        raise ValueError("CISD after boundary must be timezone-aware")
    if before.tzinfo is None or before.utcoffset() is None:
        raise ValueError("CISD before boundary must be timezone-aware")
    if before <= after:
        raise ValueError("CISD window must be positive")

    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    if ordered != bars:
        raise ValueError("CISD bars must be chronological")

    for center in range(1, len(bars) - 1):
        left, pivot, right = bars[center - 1], bars[center], bars[center + 1]
        if not (after < pivot.closed_at <= before):
            continue
        if right.closed_at > before:
            continue
        if not _swing_matches(left, pivot, right, direction):
            continue

        series = _causal_series(bars, center=center, direction=direction)
        if not series:
            continue
        boundary = series[0].source.open

        for candidate in bars[center + 1 :]:
            if candidate.closed_at > before:
                break
            if candidate.closed_at <= right.closed_at:
                continue
            crossed = (
                candidate.source.close > boundary
                if direction is CapitalizerSourceDirection.BULLISH
                else candidate.source.close < boundary
            )
            if not crossed:
                continue
            swing_price = (
                pivot.source.low
                if direction is CapitalizerSourceDirection.BULLISH
                else pivot.source.high
            )
            return V48StructuralCISDObservation(
                identity=IDENTITY,
                direction=direction,
                higher_timeframe_closure_confirmed=higher_timeframe_closure_confirmed,
                swing_occurred_at=pivot.opened_at,
                swing_price=swing_price,
                causal_series_started_at=series[0].opened_at,
                causal_series_ended_at=series[-1].closed_at,
                causal_series_open=boundary,
                confirmed_at=candidate.closed_at,
                confirmation_close=candidate.source.close,
                structural_confirmed=True,
                source_valid=higher_timeframe_closure_confirmed,
            )

    return V48StructuralCISDObservation(
        identity=IDENTITY,
        direction=direction,
        higher_timeframe_closure_confirmed=higher_timeframe_closure_confirmed,
        swing_occurred_at=None,
        swing_price=None,
        causal_series_started_at=None,
        causal_series_ended_at=None,
        causal_series_open=None,
        confirmed_at=None,
        confirmation_close=None,
        structural_confirmed=False,
        source_valid=False,
    )
