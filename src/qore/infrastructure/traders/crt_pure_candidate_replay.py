"""Causal replay detector for the CRT PURE research candidate.

This module can detect and count reconstructed CRT formations from closed candles.
It cannot create orders, authorize entry, mutate Strategy Identity, or inspect future
candles.  It remains research-only until primary-source closure promotes the candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
    CrtPureRangeOutcome,
    candidate_direction_from_turtle_soup,
    classify_range_outcome,
    range_midpoint,
)


@dataclass(frozen=True, slots=True)
class CrtPureReplayCandle:
    market: CrtPureMarket
    opened_at: datetime
    closed_at: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.closed_at.tzinfo is None:
            raise ValueError("replay candle timestamps must be timezone-aware")
        if self.closed_at <= self.opened_at:
            raise ValueError("replay candle must close after it opens")
        prices = (
            self.open_price,
            self.high_price,
            self.low_price,
            self.close_price,
        )
        if not all(value.is_finite() for value in prices):
            raise ValueError("replay candle prices must be finite")
        if self.low_price > self.high_price:
            raise ValueError("replay candle low cannot exceed high")
        if not self.low_price <= self.open_price <= self.high_price:
            raise ValueError("replay open must be inside high/low")
        if not self.low_price <= self.close_price <= self.high_price:
            raise ValueError("replay close must be inside high/low")


@dataclass(frozen=True, slots=True)
class CrtPureCandidateFormation:
    market: CrtPureMarket
    reference_opened_at: datetime
    reference_closed_at: datetime
    event_opened_at: datetime
    event_closed_at: datetime
    outcome: CrtPureRangeOutcome
    direction: CrtPureCandidateDirection | None
    reference_high: Decimal
    reference_low: Decimal
    midpoint: Decimal
    opposite_edge: Decimal | None
    causal_at: datetime
    research_only: bool = True
    execution_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.research_only:
            raise ValueError("candidate replay formation must remain research-only")
        if self.execution_authorized:
            raise ValueError("candidate replay cannot authorize execution")
        if self.causal_at != self.event_closed_at:
            raise ValueError("formation becomes causal only at observed candle close")
        if self.reference_closed_at > self.event_opened_at:
            raise ValueError("reference candle must be closed before event candle opens")


def _float(value: Decimal) -> float:
    return float(value)


def detect_candidate_formation(
    reference: CrtPureReplayCandle,
    observed: CrtPureReplayCandle,
) -> CrtPureCandidateFormation:
    if reference.market is not observed.market:
        raise ValueError("reference and observed candles must belong to the same market")
    if reference.closed_at > observed.opened_at:
        raise ValueError("candidate replay prohibits overlapping/future reference candles")

    outcome = classify_range_outcome(
        reference_high=_float(reference.high_price),
        reference_low=_float(reference.low_price),
        observed_high=_float(observed.high_price),
        observed_low=_float(observed.low_price),
        observed_close=_float(observed.close_price),
    )
    direction = candidate_direction_from_turtle_soup(
        reference_high=_float(reference.high_price),
        reference_low=_float(reference.low_price),
        observed_high=_float(observed.high_price),
        observed_low=_float(observed.low_price),
        observed_close=_float(observed.close_price),
    )
    midpoint = Decimal(
        str(range_midpoint(_float(reference.high_price), _float(reference.low_price)))
    )

    opposite_edge: Decimal | None
    if direction is CrtPureCandidateDirection.BULLISH:
        opposite_edge = reference.high_price
    elif direction is CrtPureCandidateDirection.BEARISH:
        opposite_edge = reference.low_price
    else:
        opposite_edge = None

    return CrtPureCandidateFormation(
        market=reference.market,
        reference_opened_at=reference.opened_at,
        reference_closed_at=reference.closed_at,
        event_opened_at=observed.opened_at,
        event_closed_at=observed.closed_at,
        outcome=outcome,
        direction=direction,
        reference_high=reference.high_price,
        reference_low=reference.low_price,
        midpoint=midpoint,
        opposite_edge=opposite_edge,
        causal_at=observed.closed_at,
    )


def scan_candidate_formations(
    candles: tuple[CrtPureReplayCandle, ...],
) -> tuple[CrtPureCandidateFormation, ...]:
    if len(candles) < 2:
        return ()

    ordered = tuple(sorted(candles, key=lambda candle: candle.opened_at))
    if ordered != candles:
        raise ValueError("replay candles must be supplied in chronological order")
    if len({item.market for item in candles}) != 1:
        raise ValueError("one replay scan must contain exactly one market")

    return tuple(
        detect_candidate_formation(reference, observed)
        for reference, observed in zip(candles[:-1], candles[1:], strict=True)
    )
