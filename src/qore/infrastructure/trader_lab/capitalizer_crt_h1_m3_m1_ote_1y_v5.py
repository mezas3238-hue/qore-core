"""QORE Capitalizer CRT H1 -> M3 MSS -> M1 OTE replay V5.

V5 is a separate experiment. V3/V4 are untouched.

Frozen chain:
    H1 N reference -> H1 N+1 sweeps N -> M5 close-back inside N
    -> M3 breaks last pre-sweep 3-candle pivot
    -> causal M1 OB
    -> Fibonacci impulse using candle bodies only
    -> price may traverse OTE 0.62-0.79 but NO entry at 0.62/0.705
    -> exact 0.79 must be reached
    -> M1 rejection OR micro-CISD at 0.79
    -> adverse M1 close through 0.79 invalidates pre-entry
    -> M1 entry only after confirmed 0.79 reaction
    -> stop beyond M1 OB + 5-pip-equivalent buffer
    -> TP1 H1 N equilibrium closes 50% and moves remainder to BE
    -> TP2 opposite H1 N extreme
    -> same-session / portfolio MAX3 ceiling.

No M1 FVG gate. No M3 CISD/body/ATR gate.
No outcome-aware filtering. No future leakage.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_crt_h1_m3_m1_1y_v4 import (
    CRTEvent,
    M3BreakEvent,
    _find_crt,
    _find_m3_break,
    _h1_windows,
    _lifecycle,
    _reference_h1,
    _stop_buffer,
    _target_geometry,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    WINDOW_END,
    WINDOW_START,
    _aware,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_CRT_H1_M3_M1_OTE_1Y_V5"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_CRT_H1_M3_M1_OTE_1Y_V5"
ENTRY_IDENTITY = (
    "H1_N_N1_CRT__M5_CLOSEBACK__M3_LAST_PRE_SWEEP_PIVOT_BREAK__"
    "M1_CAUSAL_OB__BODY_FIB__EXACT_079_REACTION_OR_INVALIDATION"
)
STOP_IDENTITY = "M1_OB_EXTREME_PLUS_5_PIP_BUFFER"
TARGET_IDENTITY = "TP1_H1_N_EQ_50PCT__BE__TP2_H1_N_OPPOSITE_EXTREME"
LOOKBACK_START = WINDOW_START - timedelta(days=14)
FIB_050 = Decimal("0.50")
FIB_062 = Decimal("0.62")
FIB_0705 = Decimal("0.705")
FIB_079 = Decimal("0.79")
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
class M1OB:
    index: int
    opened_at: datetime
    low: Decimal
    high: Decimal


@dataclass(frozen=True, slots=True)
class OTEZone:
    impulse_start: Decimal
    impulse_end: Decimal
    level_050: Decimal
    level_062: Decimal
    level_0705: Decimal
    level_079: Decimal
    zone_low: Decimal
    zone_high: Decimal


@dataclass(frozen=True, slots=True)
class OTEReaction:
    index: int
    confirmed_at: datetime
    entry_price: Decimal
    reaction_type: str
    level_079_touched: bool


@dataclass(frozen=True, slots=True)
class V5Trade:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_n_opened_at: str
    h1_n_closed_at: str
    h1_n_high: str
    h1_n_low: str
    h1_n_equilibrium: str
    h1_n1_opened_at: str
    h1_n1_deadline: str
    h1_sweep_at: str
    h1_sweep_extreme: str
    m5_closeback_at: str
    m3_swing_occurred_at: str
    m3_swing_confirmed_at: str
    m3_swing_price: str
    m3_mss_confirmed_at: str
    m1_ob_opened_at: str
    m1_ob_low: str
    m1_ob_high: str
    fib_impulse_start: str
    fib_impulse_end: str
    fib_050: str
    fib_062: str
    fib_0705: str
    fib_079: str
    ote_zone_low: str
    ote_zone_high: str
    ote_reaction_type: str
    level_079_touched: bool
    entry_at: str
    entry_price: str
    stop_price: str
    stop_buffer_price: str
    tp1_price: str
    tp2_price: str
    tp1_hit: bool
    tp2_hit: bool
    exit_at: str
    exit_reason: str
    realized_r: str
    m1_bars_held: int
    same_minute_ambiguity: bool
    entry_definition: str = ENTRY_IDENTITY
    stop_definition: str = STOP_IDENTITY
    target_definition: str = TARGET_IDENTITY
    fvg_required: bool = False
    ote_required: bool = True
    fib_body_anchors_only: bool = True
    m3_cisd_required: bool = False
    m3_body_threshold_required: bool = False
    m3_atr_threshold_required: bool = False
    max3_is_ceiling_not_quota: bool = True
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class V5Metrics:
    trades: int
    wins: int
    losses: int
    flats: int
    total_r: str
    mean_r: str
    gross_profit_r: str
    gross_loss_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    stop_exits: int
    tp1_exits: int
    tp2_exits: int
    session_exits: int
    tp1_hits: int
    tp2_hits: int
    ambiguous_stop_first_exits: int


@dataclass(frozen=True, slots=True)
class V5MarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    operating_sessions_scanned: int
    h1_candles_evaluated: int
    h1_sweeps_detected: int
    m5_closebacks_confirmed: int
    m3_mss_confirmed: int
    m1_ob_identified: int
    ote_zones_defined: int
    ote_zone_interactions: int
    ote_79_touches: int
    ote_reactions_confirmed_79: int
    invalidated_close_through_79: int
    entries_executed: int
    target_geometry_invalid: int
    raw_metrics: V5Metrics | None
    stage_counts: tuple[tuple[str, int], ...]
    buffer_price: str
    architecture_predeclared: bool = True
    methodology_research_only: bool = True
    reference_rule: str = "IMMEDIATELY_PREVIOUS_COMPLETED_H1"
    m3_swing_rule: str = "LAST_3_CANDLE_PIVOT_FORMED_PRE_SWEEP"
    fib_anchor_rule: str = "M1_BODY_SWEEP_TO_M3_BREAK_BODY_EXTREME"
    ote_zone: str = "0.62_TO_0.79"
    ote_sweet_spot: str = "0.705_REFERENCE_ONLY_NO_ENTRY"
    entry_level: str = "0.79_REQUIRED"
    reaction_rule: str = "M1_REJECTION_OR_MICRO_CISD_AT_079"
    pre_entry_invalidation_rule: str = "M1_CLOSE_THROUGH_079"
    fvg_required: bool = False
    m3_cisd_required: bool = False
    m3_body_threshold_required: bool = False
    m3_atr_threshold_required: bool = False
    stop_buffer_pips: str = "5"
    tp1_fraction: str = "0.5"
    tp1_moves_stop_to_be: bool = True
    max3_is_ceiling_not_quota: bool = True
    fresh_holdout_claimed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _metrics(trades: tuple[V5Trade, ...]) -> V5Metrics | None:
    if not trades:
        return None
    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    values = tuple(Decimal(item.realized_r) for item in ordered)
    gross_profit = sum((x for x in values if x > 0), Decimal("0"))
    gross_loss = -sum((x for x in values if x < 0), Decimal("0"))
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
    return V5Metrics(
        trades=len(ordered),
        wins=sum(x > 0 for x in values),
        losses=sum(x < 0 for x in values),
        flats=sum(x == 0 for x in values),
        total_r=str(total),
        mean_r=str(total / Decimal(len(values))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=None if gross_loss == 0 else str(gross_profit / gross_loss),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=sum(x.exit_reason == "STOP" for x in ordered),
        tp1_exits=sum(x.exit_reason == "TP1" for x in ordered),
        tp2_exits=sum(x.exit_reason == "TP2" for x in ordered),
        session_exits=sum(x.exit_reason == "SESSION_EXIT" for x in ordered),
        tp1_hits=sum(x.tp1_hit for x in ordered),
        tp2_hits=sum(x.tp2_hit for x in ordered),
        ambiguous_stop_first_exits=sum(
            x.same_minute_ambiguity for x in ordered
        ),
    )


def _find_ob(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    crt: CRTEvent,
    mss: M3BreakEvent,
) -> M1OB | None:
    break_indices = [
        index
        for index, bar in enumerate(execution)
        if mss.break_opened_at <= bar.opened_at < mss.break_confirmed_at
    ]
    if not break_indices:
        return None
    first_break = break_indices[0]
    for index in range(first_break - 1, -1, -1):
        bar = execution[index]
        if bar.opened_at < crt.sweep_at:
            break
        opposing = (
            bar.close < bar.open
            if crt.side is CapitalizerSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            return M1OB(
                index=index,
                opened_at=bar.opened_at,
                low=bar.low,
                high=bar.high,
            )
    return None


def _find_bar_at(
    execution: tuple[CapitalizerM1Bar, ...],
    opened_at: datetime,
) -> CapitalizerM1Bar | None:
    for bar in execution:
        if bar.opened_at == opened_at:
            return bar
    return None


def _define_ote(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    crt: CRTEvent,
    mss: M3BreakEvent,
) -> OTEZone | None:
    sweep_bar = _find_bar_at(execution, crt.sweep_at)
    break_bars = tuple(
        bar
        for bar in execution
        if mss.break_opened_at <= bar.opened_at < mss.break_confirmed_at
    )
    if sweep_bar is None or not break_bars:
        return None

    if crt.side is CapitalizerSide.LONG:
        start = min(sweep_bar.open, sweep_bar.close)
        end = max(max(bar.open, bar.close) for bar in break_bars)
        if end <= start:
            return None
        span = end - start
        level_050 = end - FIB_050 * span
        level_062 = end - FIB_062 * span
        level_0705 = end - FIB_0705 * span
        level_079 = end - FIB_079 * span
        zone_low = level_079
        zone_high = level_062
    else:
        start = max(sweep_bar.open, sweep_bar.close)
        end = min(min(bar.open, bar.close) for bar in break_bars)
        if end >= start:
            return None
        span = start - end
        level_050 = end + FIB_050 * span
        level_062 = end + FIB_062 * span
        level_0705 = end + FIB_0705 * span
        level_079 = end + FIB_079 * span
        zone_low = level_062
        zone_high = level_079

    return OTEZone(
        impulse_start=start,
        impulse_end=end,
        level_050=level_050,
        level_062=level_062,
        level_0705=level_0705,
        level_079=level_079,
        zone_low=zone_low,
        zone_high=zone_high,
    )


def _micro_cisd_boundary(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> Decimal | None:
    values: list[Decimal] = []
    cursor = index - 1
    while cursor >= 0:
        bar = execution[cursor]
        opposing = (
            bar.close < bar.open
            if side is CapitalizerSide.LONG
            else bar.close > bar.open
        )
        if not opposing:
            break
        values.append(bar.open)
        cursor -= 1
    if not values:
        return None
    return max(values) if side is CapitalizerSide.LONG else min(values)


def _rejection(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
) -> bool:
    body_low = min(bar.open, bar.close)
    body_high = max(bar.open, bar.close)
    if side is CapitalizerSide.LONG:
        lower_wick = body_low - bar.low
        return bar.close > bar.open and lower_wick > 0
    upper_wick = bar.high - body_high
    return bar.close < bar.open and upper_wick > 0


def _find_ote_reaction(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    zone: OTEZone,
    after: datetime,
) -> tuple[str, OTEReaction | None]:
    zone_interacted = False
    level_079_reached = False

    for index, bar in enumerate(execution):
        if bar.opened_at < after:
            continue

        touches_zone = bar.low <= zone.zone_high and bar.high >= zone.zone_low
        if touches_zone:
            zone_interacted = True

        touches_079 = bar.low <= zone.level_079 <= bar.high
        if touches_079:
            level_079_reached = True

        if not level_079_reached:
            continue

        adverse_close = (
            bar.close < zone.level_079
            if side is CapitalizerSide.LONG
            else bar.close > zone.level_079
        )
        if adverse_close:
            return "INVALIDATED_CLOSE_THROUGH_079", None

        if not touches_079:
            continue

        rejection = _rejection(bar, side=side)
        boundary = _micro_cisd_boundary(
            execution,
            index=index,
            side=side,
        )
        micro_cisd = False
        if boundary is not None:
            micro_cisd = (
                bar.close > boundary
                if side is CapitalizerSide.LONG
                else bar.close < boundary
            )

        if rejection or micro_cisd:
            reaction_type = (
                "REJECTION_AND_MICRO_CISD_AT_079"
                if rejection and micro_cisd
                else "REJECTION_AT_079"
                if rejection
                else "MICRO_CISD_AT_079"
            )
            return "REACTION_AT_079", OTEReaction(
                index=index,
                confirmed_at=bar.closed_at,
                entry_price=bar.close,
                reaction_type=reaction_type,
                level_079_touched=True,
            )

    if level_079_reached:
        return "TOUCHED_079_NO_REACTION", None
    if zone_interacted:
        return "OTE_ONLY_NO_079_TOUCH", None
    return "NO_OTE_INTERACTION", None


def _scan_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    execution: tuple[CapitalizerM1Bar, ...],
    h1: tuple[Any, ...],
    m5: tuple[Any, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[Any, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Any, ...],
    buffer_price: Decimal,
    stages: Counter[str],
) -> tuple[V5Trade, ...]:
    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return ()

    results: list[V5Trade] = []
    for n1_open, n1_deadline, hour_bars in _h1_windows(execution):
        stages["H1_CANDLES_EVALUATED"] += 1
        reference = _reference_h1(h1, before=n1_open)
        if reference is None:
            stages["H1_REFERENCE_MISSING"] += 1
            continue

        sweep_seen, crt = _find_crt(
            reference=reference,
            hour_bars=hour_bars,
            m5=m5,
            m5_closes=m5_closes,
            n1_open=n1_open,
            n1_deadline=n1_deadline,
        )
        if sweep_seen:
            stages["H1_SWEEP_DETECTED"] += 1
        if crt is None:
            if sweep_seen:
                stages["M5_CLOSEBACK_MISSING"] += 1
            continue
        stages["M5_CLOSEBACK_CONFIRMED"] += 1

        mss = _find_m3_break(
            crt=crt,
            m3=m3,
            m3_closes=m3_closes,
            m3_pivots=m3_pivots,
        )
        if mss is None:
            stages["M3_MSS_MISSING"] += 1
            continue
        stages["M3_MSS_CONFIRMED"] += 1

        ob = _find_ob(execution, crt=crt, mss=mss)
        if ob is None:
            stages["M1_OB_MISSING"] += 1
            continue
        stages["M1_OB_IDENTIFIED"] += 1

        zone = _define_ote(execution, crt=crt, mss=mss)
        if zone is None:
            stages["OTE_ZONE_INVALID"] += 1
            continue
        stages["OTE_ZONE_DEFINED"] += 1

        ote_status, reaction = _find_ote_reaction(
            execution,
            side=crt.side,
            zone=zone,
            after=mss.break_confirmed_at,
        )
        if ote_status != "NO_OTE_INTERACTION":
            stages["OTE_ZONE_INTERACTION"] += 1
        if ote_status in {
            "TOUCHED_079_NO_REACTION",
            "INVALIDATED_CLOSE_THROUGH_079",
            "REACTION_AT_079",
        }:
            stages["OTE_079_TOUCH"] += 1
        if ote_status == "INVALIDATED_CLOSE_THROUGH_079":
            stages["OTE_INVALIDATED_CLOSE_THROUGH_079"] += 1
            continue
        if reaction is None:
            stages[f"OTE_NO_ENTRY_{ote_status}"] += 1
            continue
        stages["OTE_REACTION_CONFIRMED_079"] += 1

        entry_price = reaction.entry_price
        stop_price = (
            ob.low - buffer_price
            if crt.side is CapitalizerSide.LONG
            else ob.high + buffer_price
        )
        valid_stop = (
            stop_price < entry_price
            if crt.side is CapitalizerSide.LONG
            else stop_price > entry_price
        )
        if not valid_stop:
            stages["M1_OB_STOP_INVALID"] += 1
            continue

        targets = _target_geometry(crt=crt, entry_price=entry_price)
        if targets is None:
            stages["TARGET_GEOMETRY_INVALID"] += 1
            continue
        tp1_price, tp2_price = targets

        (
            realized,
            reason,
            tp1_hit,
            tp2_hit,
            held,
            ambiguous,
            exit_at,
        ) = _lifecycle(
            execution,
            entry_index=reaction.index,
            side=crt.side,
            entry_price=entry_price,
            stop_price=stop_price,
            tp1_price=tp1_price,
            tp2_price=tp2_price,
        )
        stages["ENTRY_EXECUTED"] += 1
        if tp1_hit:
            stages["TP1_HIT"] += 1
        if tp2_hit:
            stages["TP2_HIT"] += 1
        stages[f"EXIT_{reason}"] += 1

        results.append(
            V5Trade(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=crt.side.value,
                h1_n_opened_at=crt.reference_opened_at.isoformat(),
                h1_n_closed_at=crt.reference_closed_at.isoformat(),
                h1_n_high=str(crt.reference_high),
                h1_n_low=str(crt.reference_low),
                h1_n_equilibrium=str(crt.reference_eq),
                h1_n1_opened_at=crt.n1_opened_at.isoformat(),
                h1_n1_deadline=crt.n1_deadline.isoformat(),
                h1_sweep_at=crt.sweep_at.isoformat(),
                h1_sweep_extreme=str(crt.sweep_extreme),
                m5_closeback_at=crt.m5_closeback_at.isoformat(),
                m3_swing_occurred_at=mss.swing_occurred_at.isoformat(),
                m3_swing_confirmed_at=mss.swing_confirmed_at.isoformat(),
                m3_swing_price=str(mss.swing_price),
                m3_mss_confirmed_at=mss.break_confirmed_at.isoformat(),
                m1_ob_opened_at=ob.opened_at.isoformat(),
                m1_ob_low=str(ob.low),
                m1_ob_high=str(ob.high),
                fib_impulse_start=str(zone.impulse_start),
                fib_impulse_end=str(zone.impulse_end),
                fib_050=str(zone.level_050),
                fib_062=str(zone.level_062),
                fib_0705=str(zone.level_0705),
                fib_079=str(zone.level_079),
                ote_zone_low=str(zone.zone_low),
                ote_zone_high=str(zone.zone_high),
                ote_reaction_type=reaction.reaction_type,
                level_079_touched=reaction.level_079_touched,
                entry_at=execution[reaction.index].opened_at.isoformat(),
                entry_price=str(entry_price),
                stop_price=str(stop_price),
                stop_buffer_price=str(buffer_price),
                tp1_price=str(tp1_price),
                tp2_price=str(tp2_price),
                tp1_hit=tp1_hit,
                tp2_hit=tp2_hit,
                exit_at=exit_at.isoformat(),
                exit_reason=reason,
                realized_r=str(realized),
                m1_bars_held=held,
                same_minute_ambiguity=ambiguous,
            )
        )

    return tuple(results)


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[V5MarketReport, tuple[V5Trade, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("V5 replay found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("V5 requires one symbol per M1 root")

    h1 = _aggregate_h1(all_bars)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_pivots = _pivots(m3)
    m5_closes = tuple(bar.closed_at for bar in m5)
    m3_closes = tuple(bar.closed_at for bar in m3)
    buffer_price = _stop_buffer(all_bars)

    execution_by_day, _ = _index_day_inputs(all_bars, session=session)
    grouped_dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat()
        <= key
        < WINDOW_END.date().isoformat()
    )

    stages: Counter[str] = Counter()
    trades: list[V5Trade] = []
    per_day: Counter[str] = Counter()
    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        produced = _scan_day(
            symbol=symbol,
            session=session,
            operating_day=operating_day,
            execution=execution_by_day.get(value, ()),
            h1=h1,
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
    report = V5MarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        operating_sessions_scanned=len(grouped_dates),
        h1_candles_evaluated=stages["H1_CANDLES_EVALUATED"],
        h1_sweeps_detected=stages["H1_SWEEP_DETECTED"],
        m5_closebacks_confirmed=stages["M5_CLOSEBACK_CONFIRMED"],
        m3_mss_confirmed=stages["M3_MSS_CONFIRMED"],
        m1_ob_identified=stages["M1_OB_IDENTIFIED"],
        ote_zones_defined=stages["OTE_ZONE_DEFINED"],
        ote_zone_interactions=stages["OTE_ZONE_INTERACTION"],
        ote_79_touches=stages["OTE_079_TOUCH"],
        ote_reactions_confirmed_79=stages["OTE_REACTION_CONFIRMED_079"],
        invalidated_close_through_79=stages["OTE_INVALIDATED_CLOSE_THROUGH_079"],
        entries_executed=len(ordered),
        target_geometry_invalid=stages["TARGET_GEOMETRY_INVALID"],
        raw_metrics=_metrics(ordered),
        stage_counts=tuple(
            sorted(stages.items(), key=lambda item: (-item[1], item[0]))
        ),
        buffer_price=str(buffer_price),
    )
    return report, ordered


def write_market(
    report: V5MarketReport,
    trades: tuple[V5Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-crt-h1-m3-m1-ote-1y-v5"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-crt-h1-m3-m1-ote-1y-v5.json"))
    if len(paths) != 9:
        raise ValueError(f"V5 matrix requires 9 reports, got {len(paths)}")
    reports: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("identity") != IDENTITY:
            raise ValueError("unexpected V5 market report")
        reports.append(dict(raw))
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("V5 universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def _load_trades(root: Path) -> tuple[V5Trade, ...]:
    rows: list[V5Trade] = []
    for path in sorted(
        root.rglob("capitalizer-*-crt-h1-m3-m1-ote-1y-v5-trades.jsonl")
    ):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V5Trade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _portfolio_max3(trades: tuple[V5Trade, ...]) -> tuple[V5Trade, ...]:
    grouped: dict[str, list[V5Trade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)
    selected: list[V5Trade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _monthly_counts(trades: tuple[V5Trade, ...]) -> dict[str, int]:
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
        sr = tuple(x for x in raw if x.session == session.value)
        sm = tuple(x for x in max3 if x.session == session.value)
        rm = _metrics(sr)
        mm = _metrics(sm)
        per_session[session.value] = {
            "raw_trades": len(sr),
            "raw_metrics": None if rm is None else asdict(rm),
            "max3_trades": len(sm),
            "max3_metrics": None if mm is None else asdict(mm),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "architecture": (
            "H1_N_N1_CRT_TO_M5_CLOSEBACK_TO_M3_LAST_PIVOT_MSS_"
            "TO_M1_OB_BODY_FIB_OTE_REACTION"
        ),
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "h1_candles_evaluated": sum(int(x["h1_candles_evaluated"]) for x in reports),
        "h1_sweeps_detected": sum(int(x["h1_sweeps_detected"]) for x in reports),
        "m5_closebacks_confirmed": sum(int(x["m5_closebacks_confirmed"]) for x in reports),
        "m3_mss_confirmed": sum(int(x["m3_mss_confirmed"]) for x in reports),
        "m1_ob_identified": sum(int(x["m1_ob_identified"]) for x in reports),
        "ote_zones_defined": sum(int(x["ote_zones_defined"]) for x in reports),
        "ote_zone_interactions": sum(int(x["ote_zone_interactions"]) for x in reports),
        "ote_79_touches": sum(int(x["ote_79_touches"]) for x in reports),
        "ote_reactions_confirmed_79": sum(int(x["ote_reactions_confirmed_79"]) for x in reports),
        "invalidated_close_through_79": sum(
            int(x["invalidated_close_through_79"])
            for x in reports
        ),
        "raw_trades": len(raw),
        "raw_metrics": None if raw_metrics is None else asdict(raw_metrics),
        "max3_selected_trades": len(max3),
        "max3_metrics": None if max3_metrics is None else asdict(max3_metrics),
        "days_with_any_trade": len({x.operating_date for x in max3}),
        "monthly_max3_trades": _monthly_counts(max3),
        "per_session": per_session,
        "markets": reports,
        "max3_stop_exits": sum(x.exit_reason == "STOP" for x in max3),
        "max3_tp1_exits": sum(x.exit_reason == "TP1" for x in max3),
        "max3_tp2_exits": sum(x.exit_reason == "TP2" for x in max3),
        "max3_session_exits": sum(x.exit_reason == "SESSION_EXIT" for x in max3),
        "max3_tp1_hits": sum(x.tp1_hit for x in max3),
        "max3_tp2_hits": sum(x.tp2_hit for x in max3),
        "max3_079_touches": sum(x.level_079_touched for x in max3),
        "entry_identity": ENTRY_IDENTITY,
        "stop_identity": STOP_IDENTITY,
        "target_identity": TARGET_IDENTITY,
        "fvg_required": False,
        "ote_required": True,
        "fib_body_anchors_only": True,
        "ote_zone": "0.62_TO_0.79",
        "ote_sweet_spot": "0.705_REFERENCE_ONLY_NO_ENTRY",
        "entry_level": "0.79_REQUIRED",
        "reaction_rule": "M1_REJECTION_OR_MICRO_CISD_AT_079",
        "pre_entry_invalidation_rule": "M1_CLOSE_THROUGH_079",
        "m3_cisd_required": False,
        "m3_body_threshold_required": False,
        "m3_atr_threshold_required": False,
        "stop_uses_m1_ob": True,
        "stop_buffer_pips": "5",
        "tp1_fraction": "0.5",
        "tp1_moves_stop_to_be": True,
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
    (output / "capitalizer-nine-market-crt-h1-m3-m1-ote-1y-v5.json").write_text(
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
        print(json.dumps(asdict(report), sort_keys=True))
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
