#!/usr/bin/env python3
"""Research-only paired source OFFER chronology; ONE VT31, no broker fills."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar, SessionId, Side, utc, MethodologyDecision,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.m1_execution import (
    confirmed_m1_fvg,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader
from vt31_ict_cleanroom_cog_real_3y_fast_v1 import (
    BASE, FROZEN_SOURCE_SHA256, NY, WINDOW_HOURS, _bar, _completed_hour, _stream,
)

SCHEMA = "qore.vt31.shadow_opposite_pivot_ab.source.v1"


@dataclass(frozen=True)
class Protected:
    price: Decimal
    pivot_at: datetime
    confirmed_at: datetime


def opposing_pivot(
    bars: tuple[M1Bar, ...], side: Side, shift_at: datetime,
) -> Protected | None:
    """Most recent opposing 3-M1 swing CONFIRMED before breakout M1 opens.

    This is an explicitly proposed research formalization, not an asserted
    mandatory detail of the 2023 ICT video.
    """
    older = tuple(
        b for b in bars if utc(b.closed_at) <= utc(shift_at) - timedelta(minutes=1)
    )
    for i in range(len(older) - 2, 0, -1):
        a, b, c = older[i - 1:i + 2]
        if a.closed_at != b.opened_at or b.closed_at != c.opened_at:
            continue
        if side is Side.LONG and b.low < a.low and b.low < c.low:
            return Protected(b.low, b.opened_at, c.closed_at)
        if side is Side.SHORT and b.high > a.high and b.high > c.high:
            return Protected(b.high, b.opened_at, c.closed_at)
    return None


class TracedCognition(VT31CleanroomCognition):
    """Intercept actual new MSS before any future bar; preserve exact decision."""
    def __init__(self) -> None:
        super().__init__()
        self.protected: dict[tuple[datetime, Side], Protected | None] = {}

    def assess(self, *, session: SessionId, as_of: datetime):
        result = super().assess(session=session, as_of=as_of)
        d = result.decision
        if d is not None and d.structure_break_confirmed_at == as_of:
            key = (utc(as_of), d.side)
            if key not in self.protected:
                self.protected[key] = opposing_pivot(
                    tuple(self._index._recent_mss), d.side, as_of
                )
        return result


def overlaps_ce(b: M1Bar, ce: Decimal) -> bool:
    return b.low <= ce <= b.high


def target_reached(b: M1Bar, side: Side, price: Decimal) -> bool:
    return b.high >= price if side is Side.LONG else b.low <= price


def beyond_opposing_stop_close(b: M1Bar, side: Side, price: Decimal) -> bool:
    return b.close < price if side is Side.LONG else b.close > price


def full_fvg_closed(b: M1Bar, side: Side, lo: Decimal, hi: Decimal) -> bool:
    return b.close < lo if side is Side.LONG else b.close > hi


def opposite_mss_and_fvg(
    cog: TracedCognition, recent: tuple[M1Bar, ...],
    session: SessionId, side: Side,
) -> bool:
    if len(recent) != 3:
        return False
    shift = cog._index.shift()
    if shift is None or shift.side is side:
        return False
    a, b, c = recent
    if a.closed_at != b.opened_at or b.closed_at != c.opened_at:
        return False
    f = confirmed_m1_fvg(session=session, first=a, middle=b, third=c)
    return f is not None and f.side is shift.side


@dataclass
class Shadow:
    side: Side
    source_ce: Decimal
    zone_low: Decimal
    zone_high: Decimal
    target: Decimal
    protected: Protected | None
    formed_at: datetime
    outcome: str = "OPEN"
    initial_ce_at: datetime | None = None
    exit_after_ce: str = "NOT_STARTED"

    def on_m1(
        self, bar: M1Bar, cog: TracedCognition,
        recent: tuple[M1Bar, ...], session: SessionId,
    ) -> None:
        if bar.closed_at <= self.formed_at:
            return
        if self.protected is None:
            self.outcome = "UNPROVEN_PROTECTED_SWING"
            return
        if self.initial_ce_at is not None:
            if self.exit_after_ce != "UNRESOLVED":
                return
            t = target_reached(bar, self.side, self.target)
            stop = (
                bar.low <= self.protected.price
                if self.side is Side.LONG else bar.high >= self.protected.price
            )
            if t and stop:
                self.exit_after_ce = "SAME_M1_TARGET_STOP_UNKNOWN"
            elif t:
                self.exit_after_ce = "MID_ONLY_TARGET_AFTER_CE"
            elif stop:
                self.exit_after_ce = "MID_ONLY_STOP_AFTER_CE"
            return
        if self.outcome != "OPEN":
            return
        ce = overlaps_ce(bar, self.source_ce)
        draw = target_reached(bar, self.side, self.target)
        protected = beyond_opposing_stop_close(
            bar, self.side, self.protected.price
        )
        fvg = full_fvg_closed(
            bar, self.side, self.zone_low, self.zone_high
        )
        opposite = opposite_mss_and_fvg(cog, recent, session, self.side)
        if ce and (draw or protected or fvg or opposite):
            self.outcome = "CE_AND_CANCELLATION_SAME_M1_UNKNOWN"
        elif draw:
            self.outcome = "TARGET_BEFORE_CE"
        elif protected:
            self.outcome = "PROTECTED_SWING_CLOSE_BROKEN"
        elif opposite:
            self.outcome = "OPPOSING_MSS_DISPLACEMENT_AND_FVG"
        elif fvg:
            self.outcome = "FVG_FULL_CLOSE"
        elif ce:
            self.outcome = "CE_OVERLAP_NOT_BROKER_FILL"
            self.initial_ce_at = bar.closed_at
            self.exit_after_ce = "UNRESOLVED"

    def finish(self) -> None:
        if self.outcome == "OPEN":
            self.outcome = "WINDOW_EXPIRED_BEFORE_CE"
        if self.exit_after_ce == "UNRESOLVED":
            self.exit_after_ce = "WINDOW_END_UNKNOWN"
