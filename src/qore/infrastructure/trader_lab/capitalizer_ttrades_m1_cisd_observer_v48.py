"""Outcome-blind TTrades M1 CISD observer for Capitalizer V48.

Extracted from the useful causal portion of the consumed
capitalizer_ttrades_cisd_m1_entry_1y_replay_v1 research route.

Important V48 boundary:
- no target is consulted;
- no stop is consulted;
- no FVG is required;
- no ICT MSS/displacement is required;
- no Order Block is required for the CISD observation itself;
- no terminal outcome exists in this API.

The observer detects only:
higher-timeframe thesis already exists
-> local M1 liquidity sweep
-> causal opposing candle series
-> close through first opposing candle open (CISD).

It does not decide whether this observation is sufficient for any route. That authority
belongs to the route-specific V48 source contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_M1_CISD_OBSERVER"


class V48M1CISDStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    NO_M1_AFTER_THESIS = "NO_M1_AFTER_THESIS"
    NO_LOCAL_LIQUIDITY_SWEEP = "NO_LOCAL_LIQUIDITY_SWEEP"
    NO_OPPOSING_CAUSAL_SERIES = "NO_OPPOSING_CAUSAL_SERIES"
    NO_CISD_CLOSE = "NO_CISD_CLOSE"


@dataclass(frozen=True, slots=True)
class V48M1CISDObservation:
    identity: str
    side: CapitalizerSide
    status: V48M1CISDStatus
    thesis_at: datetime
    deadline_at: datetime
    sweep_at: datetime | None
    swept_level: Decimal | None
    sweep_extreme: Decimal | None
    causal_series_started_at: datetime | None
    causal_series_ended_at: datetime | None
    causal_series_open: Decimal | None
    causal_series_low: Decimal | None
    causal_series_high: Decimal | None
    confirmed_at: datetime | None
    confirmation_close: Decimal | None
    outcome_used: bool = False
    target_used: bool = False
    stop_used: bool = False
    fvg_required: bool = False
    ict_mss_required: bool = False
    order_block_required_for_cisd: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 M1 CISD observer identity is frozen")
        _aware(self.thesis_at)
        _aware(self.deadline_at)
        if self.deadline_at <= self.thesis_at:
            raise ValueError("CISD deadline must follow thesis time")
        if self.outcome_used or self.target_used or self.stop_used:
            raise ValueError("V48 CISD observation must be pre-economic")
        if self.fvg_required or self.ict_mss_required or self.order_block_required_for_cisd:
            raise ValueError("raw TTrades CISD cannot inherit unrelated hard gates")
        confirmed = self.status is V48M1CISDStatus.CONFIRMED
        payload_complete = all(
            value is not None
            for value in (
                self.sweep_at,
                self.swept_level,
                self.sweep_extreme,
                self.causal_series_started_at,
                self.causal_series_ended_at,
                self.causal_series_open,
                self.causal_series_low,
                self.causal_series_high,
                self.confirmed_at,
                self.confirmation_close,
            )
        )
        if confirmed != payload_complete:
            raise ValueError("CISD confirmed status/payload mismatch")
        if self.confirmed_at is not None and self.confirmed_at > self.deadline_at:
            raise ValueError("CISD cannot confirm after route deadline")

    @property
    def confirmed(self) -> bool:
        return self.status is V48M1CISDStatus.CONFIRMED


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("V48 M1 CISD timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _ordered_window(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    thesis_at: datetime,
    deadline_at: datetime,
) -> tuple[CapitalizerM1Bar, ...]:
    thesis = _aware(thesis_at)
    deadline = _aware(deadline_at)
    if deadline <= thesis:
        raise ValueError("deadline must follow thesis")
    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    if ordered != bars:
        raise ValueError("M1 CISD bars must be chronological")
    return tuple(
        bar for bar in bars
        if bar.opened_at >= thesis and bar.closed_at <= deadline
    )


def _pivot_indices(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    before_index: int,
    side: CapitalizerSide,
) -> tuple[int, ...]:
    """Return causal short-term pivots whose right-hand confirmation already exists."""

    result: list[int] = []
    for index in range(1, min(before_index, len(bars) - 1)):
        left = bars[index - 1]
        center = bars[index]
        right = bars[index + 1]
        if right.closed_at > bars[before_index].opened_at:
            break
        if side is CapitalizerSide.LONG:
            if center.low < left.low and center.low < right.low:
                result.append(index)
        else:
            if center.high > left.high and center.high > right.high:
                result.append(index)
    return tuple(result)


def _opposing(bar: CapitalizerM1Bar, side: CapitalizerSide) -> bool:
    return (
        bar.close < bar.open
        if side is CapitalizerSide.LONG
        else bar.close > bar.open
    )


def _series_ending_at(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    end_index: int,
    side: CapitalizerSide,
) -> tuple[int, ...]:
    selected: list[int] = []
    cursor = end_index
    while cursor >= 0 and _opposing(bars[cursor], side):
        selected.append(cursor)
        cursor -= 1
    selected.reverse()
    return tuple(selected)


def _failed(
    *,
    side: CapitalizerSide,
    status: V48M1CISDStatus,
    thesis_at: datetime,
    deadline_at: datetime,
) -> V48M1CISDObservation:
    return V48M1CISDObservation(
        identity=IDENTITY,
        side=side,
        status=status,
        thesis_at=thesis_at,
        deadline_at=deadline_at,
        sweep_at=None,
        swept_level=None,
        sweep_extreme=None,
        causal_series_started_at=None,
        causal_series_ended_at=None,
        causal_series_open=None,
        causal_series_low=None,
        causal_series_high=None,
        confirmed_at=None,
        confirmation_close=None,
    )


def observe_first_m1_cisd(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    thesis_at: datetime,
    deadline_at: datetime,
    side: CapitalizerSide,
) -> V48M1CISDObservation:
    """Return first causal post-thesis local-sweep CISD before the route deadline."""

    window = _ordered_window(
        bars,
        thesis_at=thesis_at,
        deadline_at=deadline_at,
    )
    if len(window) < 4:
        return _failed(
            side=side,
            status=V48M1CISDStatus.NO_M1_AFTER_THESIS,
            thesis_at=thesis_at,
            deadline_at=deadline_at,
        )

    saw_sweep = False
    saw_series = False

    for sweep_index in range(2, len(window) - 1):
        pivots = _pivot_indices(
            window,
            before_index=sweep_index,
            side=side,
        )
        if not pivots:
            continue
        pivot = window[pivots[-1]]
        sweep_bar = window[sweep_index]
        swept_level = pivot.low if side is CapitalizerSide.LONG else pivot.high
        swept = (
            sweep_bar.low < swept_level
            if side is CapitalizerSide.LONG
            else sweep_bar.high > swept_level
        )
        if not swept:
            continue
        saw_sweep = True

        series_indices = _series_ending_at(
            window,
            end_index=sweep_index,
            side=side,
        )
        if not series_indices:
            probe = sweep_index + 1
            while probe < len(window) - 1:
                if _opposing(window[probe], side):
                    series_indices = _series_ending_at(
                        window,
                        end_index=probe,
                        side=side,
                    )
                    break
                probe += 1
        if not series_indices:
            continue
        saw_series = True

        series = tuple(window[index] for index in series_indices)
        boundary = series[0].open
        confirmation_start = series_indices[-1] + 1
        for confirmation_index in range(confirmation_start, len(window)):
            bar = window[confirmation_index]
            crossed = (
                bar.close > boundary
                if side is CapitalizerSide.LONG
                else bar.close < boundary
            )
            if not crossed:
                continue
            return V48M1CISDObservation(
                identity=IDENTITY,
                side=side,
                status=V48M1CISDStatus.CONFIRMED,
                thesis_at=thesis_at,
                deadline_at=deadline_at,
                sweep_at=sweep_bar.closed_at,
                swept_level=swept_level,
                sweep_extreme=(
                    sweep_bar.low
                    if side is CapitalizerSide.LONG
                    else sweep_bar.high
                ),
                causal_series_started_at=series[0].opened_at,
                causal_series_ended_at=series[-1].closed_at,
                causal_series_open=boundary,
                causal_series_low=min(item.low for item in series),
                causal_series_high=max(item.high for item in series),
                confirmed_at=bar.closed_at,
                confirmation_close=bar.close,
            )

    return _failed(
        side=side,
        status=(
            V48M1CISDStatus.NO_OPPOSING_CAUSAL_SERIES
            if saw_sweep and not saw_series
            else V48M1CISDStatus.NO_CISD_CLOSE
            if saw_series
            else V48M1CISDStatus.NO_LOCAL_LIQUIDITY_SWEEP
        ),
        thesis_at=thesis_at,
        deadline_at=deadline_at,
    )
