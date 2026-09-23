"""Causal SOURCE_FIRST CISD helper with post-sweep opposing-series rearm.

Frozen from outcome-free structural evidence:
- observation begins strictly after the actual liquidity sweep;
- each distinct contiguous opposing M3 series establishes a boundary at the OPEN
  of the first candle in that series;
- boundary persists until a later distinct opposing series begins;
- a later opposing series may rearm the hypothesis by replacing the old boundary;
- pre-sweep candles never establish a boundary;
- confirmation after M5 closeback must still satisfy frozen V3 direction,
  swing-break, body>=60%, range>1.2*ATR, and close through current boundary.

No outcomes are read.
"""

from __future__ import annotations

import bisect
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    TFBar,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_SERIES_REARM_V1"
BOUNDARY_SEMANTICS = "FIRST_OPPOSING_OPEN_PER_DISTINCT_POST_SWEEP_SERIES"


def _opposing(bar: TFBar, side: CapitalizerSide) -> bool:
    source = bar.source
    return bool(
        source.close < source.open
        if side is CapitalizerSide.LONG
        else source.close > source.open
    )


def _crossed(
    close: Decimal,
    boundary: Decimal,
    side: CapitalizerSide,
) -> bool:
    return bool(
        close > boundary
        if side is CapitalizerSide.LONG
        else close < boundary
    )


def find_series_rearm_m3_mss(
    bars: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    pivots: tuple[Pivot, ...],
    *,
    sweep_at: datetime,
    after: datetime,
    before: datetime,
    side: CapitalizerSide,
) -> v3.M3MssEvent | None:
    if sweep_at > after or after > before:
        raise ValueError(
            "series-rearm CISD requires sweep_at <= closeback_at <= deadline"
        )
    if after == before:
        return None

    start = bisect.bisect_right(closes, sweep_at)
    end = bisect.bisect_right(closes, before)
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"

    boundary: Decimal | None = None
    in_opposing_series = False

    for index in range(start, end):
        bar = bars[index]
        source = bar.source

        if _opposing(bar, side):
            if not in_opposing_series:
                boundary = source.open
            in_opposing_series = True
            continue

        in_opposing_series = False
        if bar.closed_at <= after or boundary is None:
            continue

        full_range = source.high - source.low
        if full_range <= 0:
            continue

        directional = (
            source.close > source.open
            if side is CapitalizerSide.LONG
            else source.close < source.open
        )
        if not directional:
            continue

        body_ratio = abs(source.close - source.open) / full_range
        if body_ratio < v3.BODY_RATIO_MIN:
            continue

        atr = v3._atr14(bars, index)
        if atr is None or full_range <= v3.ATR_MULTIPLIER * atr:
            continue

        broken = v3._latest_pivot(
            pivots,
            before=bar.opened_at,
            kind=break_kind,
        )
        if broken is None:
            continue

        structure_break = (
            source.close > broken.price
            if side is CapitalizerSide.LONG
            else source.close < broken.price
        )
        if not structure_break or not _crossed(source.close, boundary, side):
            continue

        return v3.M3MssEvent(
            side=side,
            confirmed_at=bar.closed_at,
            displacement_opened_at=bar.opened_at,
            displacement_closed_at=bar.closed_at,
            broken_swing_price=broken.price,
            cisd_boundary=boundary,
            body_ratio=body_ratio,
            atr14=atr,
            displacement_range=full_range,
        )

    return None
