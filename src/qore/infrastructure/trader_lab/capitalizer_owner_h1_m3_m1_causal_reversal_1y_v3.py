"""QORE Capitalizer H1 sweep -> M3 MSS -> M1 causal entry replay V3."""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    ICTReplayMetrics,
    WINDOW_END,
    WINDOW_START,
    _aware,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    ReferenceLiquidity,
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_OWNER_H1_M3_M1_CAUSAL_REVERSAL_1Y_V3"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_"
    "OWNER_H1_M3_M1_CAUSAL_REVERSAL_1Y_V3"
)
ENTRY_IDENTITY = (
    "H1_SWEEP__M5_CLOSEBACK__M3_MSS_CISD_ATR__"
    "M1_CAUSAL_OB_FVG_RETEST_OR_CE"
)
STOP_IDENTITY = "M3_BROKEN_SWING_PLUS_5_PIP_BUFFER"
TARGET_IDENTITY = "FIXED_2R_OR_NEXT_H1_OPEN"
LOOKBACK_START = WINDOW_START - timedelta(days=21)
NEW_YORK = ZoneInfo("America/New_York")
BODY_RATIO_MIN = Decimal("0.60")
ATR_MULTIPLIER = Decimal("1.2")
BUFFER_PIPS = Decimal("5")
EXPECTED_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
}


@dataclass(frozen=True, slots=True)
class LiquidityLevel:
    kind: str
    price: Decimal
    source: str


@dataclass(frozen=True, slots=True)
class H1Swing:
    kind: str
    price: Decimal
    confirmed_at: datetime


@dataclass(frozen=True, slots=True)
class SweepCloseback:
    side: CapitalizerSide
    reference: LiquidityLevel
    sweep_at: datetime
    sweep_extreme: Decimal
    closeback_at: datetime
    h1_open: datetime
    h1_deadline: datetime


@dataclass(frozen=True, slots=True)
class M3MssEvent:
    side: CapitalizerSide
    confirmed_at: datetime
    displacement_opened_at: datetime
    displacement_closed_at: datetime
    broken_swing_price: Decimal
    cisd_boundary: Decimal
    body_ratio: Decimal
    atr14: Decimal
    displacement_range: Decimal


@dataclass(frozen=True, slots=True)
class M1EntryZone:
    ob_opened_at: datetime
    ob_low: Decimal
    ob_high: Decimal
    fvg_confirmed_at: datetime
    fvg_low: Decimal
    fvg_high: Decimal
    overlap_low: Decimal | None
    overlap_high: Decimal | None


@dataclass(frozen=True, slots=True)
class V3Trade:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    h1_deadline: str
    liquidity_source: str
    liquidity_kind: str
    liquidity_price: str
    h1_sweep_at: str
    h1_sweep_extreme: str
    m5_closeback_at: str
    m3_mss_at: str
    m3_broken_swing_price: str
    m3_cisd_boundary: str
    m3_body_ratio: str
    m3_atr14: str
    m3_displacement_range: str
    m1_ob_opened_at: str
    m1_ob_low: str
    m1_ob_high: str
    m1_fvg_confirmed_at: str
    m1_fvg_low: str
    m1_fvg_high: str
    m1_ob_fvg_overlap: bool
    entry_mode: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    stop_buffer_price: str
    target_price: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    same_minute_stop_target_ambiguity: bool
    entry_definition: str = ENTRY_IDENTITY
    stop_definition: str = STOP_IDENTITY
    target_definition: str = TARGET_IDENTITY
    h1_final_close_used_for_signal: bool = False
    m5_closeback_required: bool = True
    m5_mss_required: bool = False
    m3_mss_required: bool = True
    m3_body_ratio_min: str = "0.60"
    m3_atr_multiplier: str = "1.2"
    m1_entry_causally_linked_to_m3: bool = True
    max3_is_ceiling_not_quota: bool = True
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class V3MarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    operating_sessions_scanned: int
    h1_hours_scanned: int
    h1_hours_with_liquidity: int
    h1_sweeps_detected: int
    m5_closebacks_confirmed: int
    m3_mss_confirmed: int
    m1_causal_fvg_confirmed: int
    m1_ob_fvg_confluence: int
    entries_executed: int
    raw_metrics: ICTReplayMetrics | None
    raw_stop_exits: int
    raw_target_exits: int
    raw_time_exits: int
    raw_session_exits: int
    sessions_with_entry: int
    max_entries_one_market_session: int
    buffer_price: str
    stage_counts: tuple[tuple[str, int], ...]
    architecture_predeclared: bool = True
    methodology_research_only: bool = True
    entry_timeframe: str = "M1"
    confirmation_timeframe: str = "M3"
    narrative_timeframe: str = "H1"
    closeback_timeframe: str = "M5"
    h1_final_close_used_for_signal: bool = False
    m5_mss_required: bool = False
    m3_mss_required: bool = True
    m3_body_ratio_min: str = "0.60"
    m3_atr_multiplier: str = "1.2"
    stop_buffer_pips: str = "5"
    stop_buffer_model: str = "5_X_10_X_MIN_DECIMAL_QUANTUM"
    m1_entry_causally_linked_to_m3: bool = True
    max3_is_ceiling_not_quota: bool = True
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _metrics(trades: tuple[V3Trade, ...]) -> ICTReplayMetrics | None:
    if not trades:
        return None
    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    values = tuple(Decimal(item.realized_gross_r) for item in ordered)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    total = sum(values, Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return ICTReplayMetrics(
        trades=len(values),
        wins=sum(value > 0 for value in values),
        losses=sum(value < 0 for value in values),
        flats=sum(value == 0 for value in values),
        total_r=str(total),
        mean_r=str(total / Decimal(len(values))),
        gross_profit_r=str(gp),
        gross_loss_r=str(gl),
        profit_factor=None if gl == 0 else str(gp / gl),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=sum(item.exit_reason == "STOP" for item in ordered),
        target_exits=sum(item.exit_reason == "TARGET" for item in ordered),
        session_exits=sum(
            item.exit_reason == "SESSION_EXIT" for item in ordered
        ),
        ambiguous_stop_first_exits=sum(
            item.same_minute_stop_target_ambiguity for item in ordered
        ),
    )


def _price_quantum(bars: tuple[CapitalizerM1Bar, ...]) -> Decimal:
    exponent = min(
        value.as_tuple().exponent
        for bar in bars[: min(len(bars), 10000)]
        for value in (bar.open, bar.high, bar.low, bar.close)
    )
    return Decimal(1).scaleb(exponent)


def _stop_buffer(bars: tuple[CapitalizerM1Bar, ...]) -> Decimal:
    return _price_quantum(bars) * Decimal("10") * BUFFER_PIPS


def _h1_hour_bounds(moment: datetime) -> tuple[datetime, datetime]:
    local = moment.astimezone(NEW_YORK)
    opened = local.replace(minute=0, second=0, microsecond=0)
    deadline = opened + timedelta(hours=1)
    return (
        opened.astimezone(moment.tzinfo),
        deadline.astimezone(moment.tzinfo),
    )


def _h1_windows(
    execution: tuple[CapitalizerM1Bar, ...],
) -> tuple[tuple[datetime, datetime, tuple[CapitalizerM1Bar, ...]], ...]:
    grouped: dict[datetime, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in execution:
        opened, _ = _h1_hour_bounds(bar.opened_at)
        grouped[opened].append(bar)
    return tuple(
        (opened, _h1_hour_bounds(opened)[1], tuple(grouped[opened]))
        for opened in sorted(grouped)
    )


def _build_h1_swings(
    h1: tuple[AggregatedBar, ...],
) -> tuple[H1Swing, ...]:
    result: list[H1Swing] = []
    for index in range(2, len(h1) - 2):
        bar = h1[index]
        left = h1[index - 2 : index]
        right = h1[index + 1 : index + 3]
        high = bar.source.high
        low = bar.source.low
        if all(high > item.source.high for item in left + right):
            result.append(
                H1Swing("HIGH", high, h1[index + 2].closed_at)
            )
        if all(low < item.source.low for item in left + right):
            result.append(
                H1Swing("LOW", low, h1[index + 2].closed_at)
            )
    return tuple(sorted(result, key=lambda item: item.confirmed_at))


def _latest_h1_swing(
    swings: tuple[H1Swing, ...],
    *,
    before: datetime,
    kind: str,
) -> H1Swing | None:
    for swing in reversed(swings):
        if swing.kind == kind and swing.confirmed_at <= before:
            return swing
    return None


def _previous_day_range(
    all_bars: tuple[CapitalizerM1Bar, ...],
    *,
    operating_day: date,
) -> tuple[Decimal, Decimal] | None:
    for offset in range(1, 5):
        prior = operating_day - timedelta(days=offset)
        chunk = tuple(
            bar
            for bar in all_bars
            if bar.opened_at.astimezone(NEW_YORK).date() == prior
        )
        if len(chunk) >= 60:
            return (
                max(bar.high for bar in chunk),
                min(bar.low for bar in chunk),
            )
    return None


def _liquidity_levels(
    *,
    prior_session: ReferenceLiquidity | None,
    previous_day: tuple[Decimal, Decimal] | None,
    h1_swings: tuple[H1Swing, ...],
    hour_open: datetime,
) -> tuple[LiquidityLevel, ...]:
    levels: list[LiquidityLevel] = []
    if prior_session is not None:
        levels.extend(
            (
                LiquidityLevel(
                    "HIGH",
                    prior_session.high,
                    f"SESSION_HIGH:{prior_session.source}",
                ),
                LiquidityLevel(
                    "LOW",
                    prior_session.low,
                    f"SESSION_LOW:{prior_session.source}",
                ),
            )
        )
    if previous_day is not None:
        day_high, day_low = previous_day
        levels.extend(
            (
                LiquidityLevel("HIGH", day_high, "PDH"),
                LiquidityLevel("LOW", day_low, "PDL"),
            )
        )
    swing_high = _latest_h1_swing(
        h1_swings, before=hour_open, kind="HIGH"
    )
    swing_low = _latest_h1_swing(
        h1_swings, before=hour_open, kind="LOW"
    )
    if swing_high is not None:
        levels.append(
            LiquidityLevel(
                "HIGH", swing_high.price, "MAJOR_H1_SWING_HIGH"
            )
        )
    if swing_low is not None:
        levels.append(
            LiquidityLevel(
                "LOW", swing_low.price, "MAJOR_H1_SWING_LOW"
            )
        )
    unique = {(item.kind, item.price): item for item in levels}
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (item.kind, item.price, item.source),
        )
    )


def _find_sweep_closeback(
    hour_bars: tuple[CapitalizerM1Bar, ...],
    *,
    levels: tuple[LiquidityLevel, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    h1_open: datetime,
    h1_deadline: datetime,
) -> tuple[bool, SweepCloseback | None]:
    sweep_seen = False
    candidates: list[SweepCloseback] = []
    for level in levels:
        sweep_bar: CapitalizerM1Bar | None = None
        for bar in hour_bars:
            swept = (
                bar.high > level.price
                if level.kind == "HIGH"
                else bar.low < level.price
            )
            if swept:
                sweep_seen = True
                sweep_bar = bar
                break
        if sweep_bar is None:
            continue
        start = bisect.bisect_right(m5_closes, sweep_bar.opened_at)
        end = bisect.bisect_right(m5_closes, h1_deadline)
        for bar in m5[start:end]:
            closed_back = (
                bar.source.close < level.price
                if level.kind == "HIGH"
                else bar.source.close > level.price
            )
            if not closed_back:
                continue
            side = (
                CapitalizerSide.SHORT
                if level.kind == "HIGH"
                else CapitalizerSide.LONG
            )
            candidates.append(
                SweepCloseback(
                    side=side,
                    reference=level,
                    sweep_at=sweep_bar.opened_at,
                    sweep_extreme=(
                        sweep_bar.high
                        if level.kind == "HIGH"
                        else sweep_bar.low
                    ),
                    closeback_at=bar.closed_at,
                    h1_open=h1_open,
                    h1_deadline=h1_deadline,
                )
            )
            break
    if not candidates:
        return sweep_seen, None
    ordered = sorted(
        candidates,
        key=lambda item: (
            item.closeback_at,
            item.sweep_at,
            item.reference.source,
            item.reference.price,
        ),
    )
    first = ordered[0]
    if any(
        item.closeback_at == first.closeback_at
        and item.side is not first.side
        for item in ordered[1:]
    ):
        return True, None
    return True, first


def _latest_pivot(
    pivots: tuple[Pivot, ...],
    *,
    before: datetime,
    kind: str,
) -> Pivot | None:
    for pivot in reversed(pivots):
        if pivot.kind == kind and pivot.confirmed_at < before:
            return pivot
    return None


def _atr14(bars: tuple[TFBar, ...], index: int) -> Decimal | None:
    if index < 15:
        return None
    values: list[Decimal] = []
    for current in range(index - 14, index):
        source = bars[current].source
        previous_close = bars[current - 1].source.close
        values.append(
            max(
                source.high - source.low,
                abs(source.high - previous_close),
                abs(source.low - previous_close),
            )
        )
    return sum(values, Decimal("0")) / Decimal("14")


def _opposing_series_boundary(
    bars: tuple[TFBar, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> Decimal | None:
    values: list[Decimal] = []
    current = index - 1
    while current >= 0:
        source = bars[current].source
        opposing = (
            source.close < source.open
            if side is CapitalizerSide.LONG
            else source.close > source.open
        )
        if not opposing:
            break
        values.append(source.open)
        current -= 1
    if not values:
        return None
    return max(values) if side is CapitalizerSide.LONG else min(values)


def _find_m3_mss(
    bars: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    pivots: tuple[Pivot, ...],
    *,
    after: datetime,
    before: datetime,
    side: CapitalizerSide,
) -> M3MssEvent | None:
    start = bisect.bisect_right(closes, after)
    end = bisect.bisect_right(closes, before)
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    for index in range(start, end):
        bar = bars[index]
        source = bar.source
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
        if body_ratio < BODY_RATIO_MIN:
            continue
        atr = _atr14(bars, index)
        if atr is None or full_range <= ATR_MULTIPLIER * atr:
            continue
        broken = _latest_pivot(
            pivots, before=bar.opened_at, kind=break_kind
        )
        boundary = _opposing_series_boundary(
            bars, index=index, side=side
        )
        if broken is None or boundary is None:
            continue
        structure_break = (
            source.close > broken.price
            if side is CapitalizerSide.LONG
            else source.close < broken.price
        )
        cisd_break = (
            source.close > boundary
            if side is CapitalizerSide.LONG
            else source.close < boundary
        )
        if not (structure_break and cisd_break):
            continue
        return M3MssEvent(
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


def _m1_causal_zone(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: M3MssEvent,
) -> M1EntryZone | None:
    displacement_indices = [
        index
        for index, bar in enumerate(execution)
        if event.displacement_opened_at
        <= bar.opened_at
        < event.displacement_closed_at
    ]
    if not displacement_indices:
        return None
    first_index = displacement_indices[0]
    ob_index: int | None = None
    for index in range(first_index - 1, -1, -1):
        bar = execution[index]
        opposing = (
            bar.close < bar.open
            if event.side is CapitalizerSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            ob_index = index
            break
    if ob_index is None:
        return None
    ob = execution[ob_index]
    candidates: list[tuple[datetime, Decimal, Decimal]] = []
    for center in displacement_indices:
        if center <= 0 or center + 1 >= len(execution):
            continue
        first = execution[center - 1]
        third = execution[center + 1]
        if third.closed_at > event.confirmed_at:
            continue
        if event.side is CapitalizerSide.LONG:
            valid = first.high < third.low
            low, high = first.high, third.low
        else:
            valid = first.low > third.high
            low, high = third.high, first.low
        if valid:
            candidates.append((third.closed_at, low, high))
    if not candidates:
        return None
    formed_at, fvg_low, fvg_high = min(
        candidates, key=lambda item: item[0]
    )
    overlap_low = max(ob.low, fvg_low)
    overlap_high = min(ob.high, fvg_high)
    if overlap_low > overlap_high:
        overlap_low = None
        overlap_high = None
    return M1EntryZone(
        ob_opened_at=ob.opened_at,
        ob_low=ob.low,
        ob_high=ob.high,
        fvg_confirmed_at=formed_at,
        fvg_low=fvg_low,
        fvg_high=fvg_high,
        overlap_low=overlap_low,
        overlap_high=overlap_high,
    )


def _find_m1_fill(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: M3MssEvent,
    zone: M1EntryZone,
    deadline: datetime,
) -> tuple[int, Decimal, str] | None:
    ce = (zone.fvg_low + zone.fvg_high) / Decimal("2")
    ob_retest: Decimal | None = None
    if zone.overlap_low is not None and zone.overlap_high is not None:
        ob_retest = (
            zone.overlap_high
            if event.side is CapitalizerSide.LONG
            else zone.overlap_low
        )
    for index, bar in enumerate(execution):
        if bar.opened_at < event.confirmed_at:
            continue
        if bar.opened_at >= deadline:
            break
        if (
            ob_retest is not None
            and bar.low <= ob_retest <= bar.high
        ):
            return index, ob_retest, "OB_FVG_RETEST"
        if bar.low <= ce <= bar.high:
            return index, ce, "FVG_CE_50"
    return None


def _lifecycle(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    entry_index: int,
    side: CapitalizerSide,
    entry_price: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
    deadline: datetime,
) -> tuple[Decimal, str, int, bool, datetime]:
    risk = abs(entry_price - stop_price)
    if risk <= 0:
        raise ValueError("V3 lifecycle requires positive risk")
    held = 0
    last_close = entry_price
    ambiguity = False
    for index in range(entry_index, len(execution)):
        bar = execution[index]
        if index > entry_index and bar.opened_at >= deadline:
            delta = (
                bar.open - entry_price
                if side is CapitalizerSide.LONG
                else entry_price - bar.open
            )
            return delta / risk, "TIME_EXIT", held, ambiguity, bar.opened_at
        held += 1
        last_close = bar.close
        stop_hit = (
            bar.low <= stop_price
            if side is CapitalizerSide.LONG
            else bar.high >= stop_price
        )
        target_hit = (
            bar.high >= target_price
            if side is CapitalizerSide.LONG
            else bar.low <= target_price
        )
        if stop_hit:
            ambiguity = target_hit
            return Decimal("-1"), "STOP", held, ambiguity, bar.closed_at
        if target_hit:
            return Decimal("2"), "TARGET", held, False, bar.closed_at
    delta = (
        last_close - entry_price
        if side is CapitalizerSide.LONG
        else entry_price - last_close
    )
    return (
        delta / risk,
        "SESSION_EXIT",
        held,
        ambiguity,
        execution[-1].closed_at,
    )


def _scan_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    prior_session: ReferenceLiquidity | None,
    execution: tuple[CapitalizerM1Bar, ...],
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1_swings: tuple[H1Swing, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
    buffer_price: Decimal,
    stages: Counter[str],
) -> tuple[V3Trade, ...]:
    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return ()
    previous_day = _previous_day_range(
        all_bars, operating_day=operating_day
    )
    results: list[V3Trade] = []
    for h1_open, h1_deadline, hour_bars in _h1_windows(execution):
        if len(results) >= MAX_EXECUTIONS_PER_SESSION:
            break
        stages["H1_HOUR_SCANNED"] += 1
        levels = _liquidity_levels(
            prior_session=prior_session,
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        if not levels:
            stages["H1_HOUR_NO_LIQUIDITY"] += 1
            continue
        stages["H1_HOUR_WITH_LIQUIDITY"] += 1
        sweep_seen, closeback = _find_sweep_closeback(
            hour_bars,
            levels=levels,
            m5=m5,
            m5_closes=m5_closes,
            h1_open=h1_open,
            h1_deadline=h1_deadline,
        )
        if sweep_seen:
            stages["H1_SWEEP_DETECTED"] += 1
        if closeback is None:
            if sweep_seen:
                stages["M5_CLOSEBACK_MISSING"] += 1
            continue
        stages["M5_CLOSEBACK_CONFIRMED"] += 1
        mss = _find_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            after=closeback.closeback_at,
            before=h1_deadline,
            side=closeback.side,
        )
        if mss is None:
            stages["M3_MSS_MISSING"] += 1
            continue
        stages["M3_MSS_CONFIRMED"] += 1
        zone = _m1_causal_zone(execution, event=mss)
        if zone is None:
            stages["M1_CAUSAL_FVG_MISSING"] += 1
            continue
        stages["M1_CAUSAL_FVG_CONFIRMED"] += 1
        has_overlap = (
            zone.overlap_low is not None
            and zone.overlap_high is not None
        )
        if has_overlap:
            stages["M1_OB_FVG_CONFLUENCE"] += 1
        fill = _find_m1_fill(
            execution,
            event=mss,
            zone=zone,
            deadline=h1_deadline,
        )
        if fill is None:
            stages["M1_FILL_MISSING"] += 1
            continue
        entry_index, entry_price, entry_mode = fill
        stop_price = (
            mss.broken_swing_price - buffer_price
            if closeback.side is CapitalizerSide.LONG
            else mss.broken_swing_price + buffer_price
        )
        valid_stop = (
            stop_price < entry_price
            if closeback.side is CapitalizerSide.LONG
            else stop_price > entry_price
        )
        if not valid_stop:
            stages["M3_STOP_INVALID_GEOMETRY"] += 1
            continue
        risk = abs(entry_price - stop_price)
        target_price = (
            entry_price + Decimal("2") * risk
            if closeback.side is CapitalizerSide.LONG
            else entry_price - Decimal("2") * risk
        )
        realized, reason, held, ambiguous, exit_at = _lifecycle(
            execution,
            entry_index=entry_index,
            side=closeback.side,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            deadline=h1_deadline,
        )
        stages["ENTRY_EXECUTED"] += 1
        results.append(
            V3Trade(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=closeback.side.value,
                h1_open=h1_open.isoformat(),
                h1_deadline=h1_deadline.isoformat(),
                liquidity_source=closeback.reference.source,
                liquidity_kind=closeback.reference.kind,
                liquidity_price=str(closeback.reference.price),
                h1_sweep_at=closeback.sweep_at.isoformat(),
                h1_sweep_extreme=str(closeback.sweep_extreme),
                m5_closeback_at=closeback.closeback_at.isoformat(),
                m3_mss_at=mss.confirmed_at.isoformat(),
                m3_broken_swing_price=str(mss.broken_swing_price),
                m3_cisd_boundary=str(mss.cisd_boundary),
                m3_body_ratio=str(mss.body_ratio),
                m3_atr14=str(mss.atr14),
                m3_displacement_range=str(mss.displacement_range),
                m1_ob_opened_at=zone.ob_opened_at.isoformat(),
                m1_ob_low=str(zone.ob_low),
                m1_ob_high=str(zone.ob_high),
                m1_fvg_confirmed_at=zone.fvg_confirmed_at.isoformat(),
                m1_fvg_low=str(zone.fvg_low),
                m1_fvg_high=str(zone.fvg_high),
                m1_ob_fvg_overlap=has_overlap,
                entry_mode=entry_mode,
                entry_at=execution[entry_index].opened_at.isoformat(),
                exit_at=exit_at.isoformat(),
                entry_price=str(entry_price),
                stop_price=str(stop_price),
                stop_buffer_price=str(buffer_price),
                target_price=str(target_price),
                realized_gross_r=str(realized),
                exit_reason=reason,
                m1_bars_held=held,
                same_minute_stop_target_ambiguity=ambiguous,
            )
        )
    return tuple(results)


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[V3MarketReport, tuple[V3Trade, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("V3 replay found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("V3 replay requires one symbol per M1 root")
    h1 = _aggregate_h1(all_bars)
    h1_swings = _build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_pivots = _pivots(m3)
    m5_closes = tuple(item.closed_at for item in m5)
    m3_closes = tuple(item.closed_at for item in m3)
    buffer_price = _stop_buffer(all_bars)
    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars, session=session
    )
    grouped_dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat()
        <= key
        < WINDOW_END.date().isoformat()
    )
    stages: Counter[str] = Counter()
    trades: list[V3Trade] = []
    per_day: Counter[str] = Counter()
    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        produced = _scan_day(
            symbol=symbol,
            session=session,
            operating_day=operating_day,
            prior_session=reference_by_day.get(value),
            execution=execution_by_day.get(value, ()),
            all_bars=all_bars,
            h1_swings=h1_swings,
            m5=m5,
            m5_closes=m5_closes,
            m3=m3,
            m3_closes=m3_closes,
            m3_pivots=m3_pivots,
            buffer_price=buffer_price,
            stages=stages,
        )
        trades.extend(produced)
        per_day[value] += len(produced)
    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    report = V3MarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        operating_sessions_scanned=len(grouped_dates),
        h1_hours_scanned=stages["H1_HOUR_SCANNED"],
        h1_hours_with_liquidity=stages["H1_HOUR_WITH_LIQUIDITY"],
        h1_sweeps_detected=stages["H1_SWEEP_DETECTED"],
        m5_closebacks_confirmed=stages["M5_CLOSEBACK_CONFIRMED"],
        m3_mss_confirmed=stages["M3_MSS_CONFIRMED"],
        m1_causal_fvg_confirmed=stages["M1_CAUSAL_FVG_CONFIRMED"],
        m1_ob_fvg_confluence=stages["M1_OB_FVG_CONFLUENCE"],
        entries_executed=len(ordered),
        raw_metrics=_metrics(ordered),
        raw_stop_exits=sum(item.exit_reason == "STOP" for item in ordered),
        raw_target_exits=sum(
            item.exit_reason == "TARGET" for item in ordered
        ),
        raw_time_exits=sum(
            item.exit_reason == "TIME_EXIT" for item in ordered
        ),
        raw_session_exits=sum(
            item.exit_reason == "SESSION_EXIT" for item in ordered
        ),
        sessions_with_entry=sum(count > 0 for count in per_day.values()),
        max_entries_one_market_session=max(per_day.values(), default=0),
        buffer_price=str(buffer_price),
        stage_counts=tuple(
            sorted(stages.items(), key=lambda item: (-item[1], item[0]))
        ),
    )
    return report, ordered


def write_market(
    report: V3MarketReport,
    trades: tuple[V3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = (
        f"capitalizer-{report.symbol.lower()}-"
        "owner-h1-m3-m1-causal-reversal-1y-v3"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-owner-h1-m3-m1-causal-reversal-1y-v3.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"V3 matrix requires 9 reports, got {len(paths)}")
    reports: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("identity") != IDENTITY:
            raise ValueError("unexpected V3 market report")
        reports.append(dict(raw))
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("V3 universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def _load_trades(root: Path) -> tuple[V3Trade, ...]:
    rows: list[V3Trade] = []
    pattern = (
        "capitalizer-*-owner-h1-m3-m1-causal-reversal-"
        "1y-v3-trades.jsonl"
    )
    for path in sorted(root.rglob(pattern)):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V3Trade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _portfolio_max3(
    trades: tuple[V3Trade, ...],
) -> tuple[V3Trade, ...]:
    grouped: dict[str, list[V3Trade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)
    selected: list[V3Trade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _monthly_counts(trades: tuple[V3Trade, ...]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for trade in trades:
        counts[trade.operating_date[:7]] += 1
    return dict(sorted(counts.items()))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = _portfolio_max3(raw)
    raw_metrics = _metrics(raw)
    max3_metrics = _metrics(max3)
    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        session_raw = tuple(
            item for item in raw if item.session == session.value
        )
        session_max3 = tuple(
            item for item in max3 if item.session == session.value
        )
        raw_value = _metrics(session_raw)
        max3_value = _metrics(session_max3)
        per_session[session.value] = {
            "raw_trades": len(session_raw),
            "raw_metrics": (
                None if raw_value is None else asdict(raw_value)
            ),
            "max3_trades": len(session_max3),
            "max3_metrics": (
                None if max3_value is None else asdict(max3_value)
            ),
        }
    return {
        "identity": MATRIX_IDENTITY,
        "architecture": (
            "H1_SWEEP_TO_M5_CLOSEBACK_TO_M3_MSS_TO_"
            "M1_CAUSAL_OB_FVG"
        ),
        "architecture_predeclared": True,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "h1_hours_scanned": sum(
            int(item["h1_hours_scanned"]) for item in reports
        ),
        "h1_hours_with_liquidity": sum(
            int(item["h1_hours_with_liquidity"]) for item in reports
        ),
        "h1_sweeps_detected": sum(
            int(item["h1_sweeps_detected"]) for item in reports
        ),
        "m5_closebacks_confirmed": sum(
            int(item["m5_closebacks_confirmed"]) for item in reports
        ),
        "m3_mss_confirmed": sum(
            int(item["m3_mss_confirmed"]) for item in reports
        ),
        "m1_causal_fvg_confirmed": sum(
            int(item["m1_causal_fvg_confirmed"]) for item in reports
        ),
        "m1_ob_fvg_confluence": sum(
            int(item["m1_ob_fvg_confluence"]) for item in reports
        ),
        "raw_trades": len(raw),
        "raw_metrics": None if raw_metrics is None else asdict(raw_metrics),
        "max3_selected_trades": len(max3),
        "max3_metrics": (
            None if max3_metrics is None else asdict(max3_metrics)
        ),
        "raw_stop_exits": sum(
            item.exit_reason == "STOP" for item in raw
        ),
        "raw_target_exits": sum(
            item.exit_reason == "TARGET" for item in raw
        ),
        "raw_time_exits": sum(
            item.exit_reason == "TIME_EXIT" for item in raw
        ),
        "raw_session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in raw
        ),
        "max3_stop_exits": sum(
            item.exit_reason == "STOP" for item in max3
        ),
        "max3_target_exits": sum(
            item.exit_reason == "TARGET" for item in max3
        ),
        "max3_time_exits": sum(
            item.exit_reason == "TIME_EXIT" for item in max3
        ),
        "max3_session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in max3
        ),
        "monthly_max3_trades": _monthly_counts(max3),
        "days_with_any_trade": len(
            {item.operating_date for item in max3}
        ),
        "annualized_max3_trades": len(max3),
        "per_session": per_session,
        "markets": reports,
        "entry_identity": ENTRY_IDENTITY,
        "stop_identity": STOP_IDENTITY,
        "target_identity": TARGET_IDENTITY,
        "narrative_timeframe": "H1",
        "closeback_timeframe": "M5",
        "confirmation_timeframe": "M3",
        "entry_timeframe": "M1",
        "h1_final_close_used_for_signal": False,
        "m5_mss_required": False,
        "m3_mss_required": True,
        "m3_body_ratio_min": "0.60",
        "m3_atr_multiplier": "1.2",
        "stop_buffer_pips": "5",
        "stop_buffer_model": "5_X_10_X_MIN_DECIMAL_QUANTUM",
        "m1_entry_causally_linked_to_m3": True,
        "max3_is_ceiling_not_quota": True,
        "methodology_research_only": True,
        "fresh_holdout_claimed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-owner-h1-m3-m1-"
        "causal-reversal-1y-v3.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[item.value for item in CapitalizerSession],
    )
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "market":
        report, trades = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, trades, args.output)
        print(
            json.dumps(
                {
                    "symbol": report.symbol,
                    "session": report.session,
                    "trades": report.entries_executed,
                    "pf": (
                        None
                        if report.raw_metrics is None
                        else report.raw_metrics.profit_factor
                    ),
                    "dd": (
                        None
                        if report.raw_metrics is None
                        else report.raw_metrics.max_drawdown_r
                    ),
                },
                sort_keys=True,
            )
        )
        return
    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
