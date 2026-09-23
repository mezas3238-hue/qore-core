"""Source-backed persistent CISD boundary helper for Capitalizer V3 research.

This module does not alter V3 and does not execute trades.

Semantics are frozen from the already-reviewed TTrades/source contract:
- causal observation begins strictly after the actual liquidity sweep;
- the first opposing M3 candle establishes the CISD boundary at its OPEN;
- that boundary persists through subsequent M3 candles until the H1 deadline;
- later opposing candles do not replace the first causal-series open;
- a confirmation candidate must occur after the M5 closeback and must still satisfy
  every frozen V3 non-CISD requirement:
  direction + protected swing break + body>=60% + range>1.2*ATR;
- the candidate confirms only if its close crosses the persistent source boundary.

No outcome, PnL, session performance or market-specific economic information is read.
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

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_CISD_V1"
BOUNDARY_SEMANTICS = "FIRST_OPPOSING_OPEN_AFTER_SWEEP_PERSISTS"


def _opposing(
    bar: TFBar,
    *,
    side: CapitalizerSide,
) -> bool:
    source = bar.source
    return bool(
        source.close < source.open
        if side is CapitalizerSide.LONG
        else source.close > source.open
    )


def _boundary_crossed(
    *,
    close: Decimal,
    boundary: Decimal,
    side: CapitalizerSide,
) -> bool:
    return bool(
        close > boundary
        if side is CapitalizerSide.LONG
        else close < boundary
    )


def find_source_first_m3_mss(
    bars: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    pivots: tuple[Pivot, ...],
    *,
    sweep_at: datetime,
    after: datetime,
    before: datetime,
    side: CapitalizerSide,
) -> v3.M3MssEvent | None:
    """Find the first source-backed M3 MSS after a frozen V3 closeback.

    Opposing candles observed after the causal sweep may establish the boundary
    before the M5 closeback. Confirmation itself is never allowed before the
    closeback and never after the supplied H1 deadline.
    """

    if not sweep_at <= after < before:
        raise ValueError(
            "source-first CISD requires sweep_at <= closeback_at < deadline"
        )

    start = bisect.bisect_right(closes, sweep_at)
    end = bisect.bisect_right(closes, before)
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    boundary: Decimal | None = None

    for index in range(start, end):
        bar = bars[index]
        source = bar.source

        if _opposing(bar, side=side):
            if boundary is None:
                boundary = source.open
            continue

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
        if not structure_break:
            continue

        if not _boundary_crossed(
            close=source.close,
            boundary=boundary,
            side=side,
        ):
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
