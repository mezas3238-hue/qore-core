"""QORE Capitalizer CRT H1 -> M3 MSS -> M1 OB/FVG replay V4.

Frozen V4 contract:
    H1 N is the immediately preceding completed H1 candle.
    H1 N+1 sweeps N high/low.
    M5 close-back confirms return inside N in real time.
    M3 breaks the last 3-candle pivot formed before the sweep.
    No M3 CISD, body-ratio, or ATR gate.
    M1 identifies the last opposite candle that originated the M3 break
    and an FVG from that same displacement.
    Entry is only a later M1 retest of that FVG.
    Stop is beyond the M1 OB plus deterministic 5-pip-equivalent buffer.
    TP1 is H1 N equilibrium: close 50%, then BE for the remainder.
    TP2 is the opposite H1 N extreme.
    Same-session lifecycle. Portfolio MAX3/session is a ceiling.

Research only. V3 is not modified.
No outcome-aware filtering. No future leakage.
Window: [2025-09-17, 2026-09-17)
"""

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
    WINDOW_END,
    WINDOW_START,
    _aware,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_CRT_H1_M3_M1_1Y_V4"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_CRT_H1_M3_M1_1Y_V4"
ENTRY_IDENTITY = (
    "H1_N_N1_CRT__M5_CLOSEBACK__M3_LAST_PRE_SWEEP_PIVOT_BREAK__"
    "M1_CAUSAL_OB_FVG_RETEST"
)
STOP_IDENTITY = "M1_OB_EXTREME_PLUS_5_PIP_BUFFER"
TARGET_IDENTITY = "TP1_H1_N_EQ_50PCT__BE__TP2_H1_N_OPPOSITE_EXTREME"
LOOKBACK_START = WINDOW_START - timedelta(days=14)
NEW_YORK = ZoneInfo("America/New_York")
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
class CRTEvent:
    side: CapitalizerSide
    reference_opened_at: datetime
    reference_closed_at: datetime
    reference_high: Decimal
    reference_low: Decimal
    reference_eq: Decimal
    n1_opened_at: datetime
    n1_deadline: datetime
    sweep_at: datetime
    sweep_extreme: Decimal
    m5_closeback_at: datetime


@dataclass(frozen=True, slots=True)
class M3BreakEvent:
    side: CapitalizerSide
    swing_occurred_at: datetime
    swing_confirmed_at: datetime
    swing_price: Decimal
    break_opened_at: datetime
    break_confirmed_at: datetime
    break_close: Decimal


@dataclass(frozen=True, slots=True)
class M1CausalSetup:
    ob_index: int
    ob_opened_at: datetime
    ob_low: Decimal
    ob_high: Decimal
    fvg_confirmed_at: datetime
    fvg_low: Decimal
    fvg_high: Decimal
    retest_price: Decimal


@dataclass(frozen=True, slots=True)
class V4Trade:
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
    m3_break_close: str
    m1_ob_opened_at: str
    m1_ob_low: str
    m1_ob_high: str
    m1_fvg_confirmed_at: str
    m1_fvg_low: str
    m1_fvg_high: str
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
    h1_final_n1_close_used_for_signal: bool = False
    m5_closeback_required: bool = True
    m3_cisd_required: bool = False
    m3_body_threshold_required: bool = False
    m3_atr_threshold_required: bool = False
    m1_retest_required: bool = True
    m1_ce_fallback_allowed: bool = False
    stop_uses_m1_ob: bool = True
    max3_is_ceiling_not_quota: bool = True
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class V4Metrics:
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
class V4MarketReport:
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
    m1_fvg_linked: int
    m1_fvg_retests: int
    entries_executed: int
    target_geometry_invalid: int
    raw_metrics: V4Metrics | None
    stage_counts: tuple[tuple[str, int], ...]
    buffer_price: str
    architecture_predeclared: bool = True
    methodology_research_only: bool = True
    narrative_timeframe: str = "H1"
    closeback_timeframe: str = "M5"
    confirmation_timeframe: str = "M3"
    entry_timeframe: str = "M1"
    reference_rule: str = "IMMEDIATELY_PREVIOUS_COMPLETED_H1"
    m3_swing_rule: str = "LAST_3_CANDLE_PIVOT_FORMED_PRE_SWEEP"
    m3_cisd_required: bool = False
    m3_body_threshold_required: bool = False
    m3_atr_threshold_required: bool = False
    m1_retest_required: bool = True
    m1_ce_fallback_allowed: bool = False
    stop_buffer_pips: str = "5"
    stop_buffer_model: str = "5_X_10_X_MIN_DECIMAL_QUANTUM"
    tp1_fraction: str = "0.5"
    tp1_moves_stop_to_be: bool = True
    max3_is_ceiling_not_quota: bool = True
    fresh_holdout_claimed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _metrics(trades: tuple[V4Trade, ...]) -> V4Metrics | None:
    if not trades:
        return None
    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    values = tuple(Decimal(item.realized_r) for item in ordered)
    gross_profit = sum(
        (value for value in values if value > 0),
        Decimal("0"),
    )
    gross_loss = -sum(
        (value for value in values if value < 0),
        Decimal("0"),
    )
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
    return V4Metrics(
        trades=len(ordered),
        wins=sum(value > 0 for value in values),
        losses=sum(value < 0 for value in values),
        flats=sum(value == 0 for value in values),
        total_r=str(total),
        mean_r=str(total / Decimal(len(values))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=(
            None
            if gross_loss == 0
            else str(gross_profit / gross_loss)
        ),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=sum(item.exit_reason == "STOP" for item in ordered),
        tp1_exits=sum(item.exit_reason == "TP1" for item in ordered),
        tp2_exits=sum(item.exit_reason == "TP2" for item in ordered),
        session_exits=sum(
            item.exit_reason == "SESSION_EXIT" for item in ordered
        ),
        tp1_hits=sum(item.tp1_hit for item in ordered),
        tp2_hits=sum(item.tp2_hit for item in ordered),
        ambiguous_stop_first_exits=sum(
            item.same_minute_ambiguity for item in ordered
        ),
    )


def _price_quantum(bars: tuple[CapitalizerM1Bar, ...]) -> Decimal:
    exponents = [
        exponent
        for bar in bars[: min(len(bars), 10000)]
        for value in (bar.open, bar.high, bar.low, bar.close)
        if isinstance((exponent := value.as_tuple().exponent), int)
    ]
    if not exponents:
        raise ValueError("V4 requires finite decimal prices")
    return Decimal(1).scaleb(min(exponents))


def _stop_buffer(bars: tuple[CapitalizerM1Bar, ...]) -> Decimal:
    return _price_quantum(bars) * Decimal("10") * BUFFER_PIPS


def _hour_bounds(moment: datetime) -> tuple[datetime, datetime]:
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
        opened, _ = _hour_bounds(bar.opened_at)
        grouped[opened].append(bar)
    return tuple(
        (opened, _hour_bounds(opened)[1], tuple(grouped[opened]))
        for opened in sorted(grouped)
    )


def _reference_h1(
    h1: tuple[AggregatedBar, ...],
    *,
    before: datetime,
) -> AggregatedBar | None:
    eligible = tuple(bar for bar in h1 if bar.closed_at <= before)
    if not eligible:
        return None
    return eligible[-1]


def _find_crt(
    *,
    reference: AggregatedBar,
    hour_bars: tuple[CapitalizerM1Bar, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    n1_open: datetime,
    n1_deadline: datetime,
) -> tuple[bool, CRTEvent | None]:
    candidates: list[CRTEvent] = []
    sweep_seen = False

    for side in (CapitalizerSide.LONG, CapitalizerSide.SHORT):
        sweep_bar: CapitalizerM1Bar | None = None
        for bar in hour_bars:
            swept = (
                bar.low < reference.source.low
                if side is CapitalizerSide.LONG
                else bar.high > reference.source.high
            )
            if swept:
                sweep_seen = True
                sweep_bar = bar
                break
        if sweep_bar is None:
            continue

        start = bisect.bisect_right(
            m5_closes,
            sweep_bar.opened_at,
        )
        end = bisect.bisect_right(
            m5_closes,
            n1_deadline,
        )
        for m5_bar in m5[start:end]:
            closed_back = (
                m5_bar.source.close > reference.source.low
                if side is CapitalizerSide.LONG
                else m5_bar.source.close < reference.source.high
            )
            if not closed_back:
                continue
            candidates.append(
                CRTEvent(
                    side=side,
                    reference_opened_at=reference.opened_at,
                    reference_closed_at=reference.closed_at,
                    reference_high=reference.source.high,
                    reference_low=reference.source.low,
                    reference_eq=(
                        reference.source.high + reference.source.low
                    )
                    / Decimal("2"),
                    n1_opened_at=n1_open,
                    n1_deadline=n1_deadline,
                    sweep_at=sweep_bar.opened_at,
                    sweep_extreme=(
                        sweep_bar.low
                        if side is CapitalizerSide.LONG
                        else sweep_bar.high
                    ),
                    m5_closeback_at=m5_bar.closed_at,
                )
            )
            break

    if not candidates:
        return sweep_seen, None

    candidates.sort(
        key=lambda item: (
            item.m5_closeback_at,
            item.sweep_at,
            item.side.value,
        )
    )
    first = candidates[0]
    if any(
        item.m5_closeback_at == first.m5_closeback_at
        and item.side is not first.side
        for item in candidates[1:]
    ):
        return True, None
    return True, first


def _last_pre_sweep_pivot(
    pivots: tuple[Pivot, ...],
    *,
    side: CapitalizerSide,
    sweep_at: datetime,
    known_at: datetime,
) -> Pivot | None:
    kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    eligible = tuple(
        pivot
        for pivot in pivots
        if pivot.kind == kind
        and pivot.occurred_at < sweep_at
        and pivot.confirmed_at <= known_at
    )
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda pivot: (
            pivot.occurred_at,
            pivot.confirmed_at,
        ),
    )


def _find_m3_break(
    *,
    crt: CRTEvent,
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
) -> M3BreakEvent | None:
    swing = _last_pre_sweep_pivot(
        m3_pivots,
        side=crt.side,
        sweep_at=crt.sweep_at,
        known_at=crt.m5_closeback_at,
    )
    if swing is None:
        return None

    start = bisect.bisect_right(
        m3_closes,
        crt.m5_closeback_at,
    )
    end = bisect.bisect_right(
        m3_closes,
        crt.n1_deadline,
    )
    for index in range(start, end):
        bar = m3[index]
        broken = (
            bar.source.close > swing.price
            if crt.side is CapitalizerSide.LONG
            else bar.source.close < swing.price
        )
        if broken:
            return M3BreakEvent(
                side=crt.side,
                swing_occurred_at=swing.occurred_at,
                swing_confirmed_at=swing.confirmed_at,
                swing_price=swing.price,
                break_opened_at=bar.opened_at,
                break_confirmed_at=bar.closed_at,
                break_close=bar.source.close,
            )
    return None


def _m1_causal_setup(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    crt: CRTEvent,
    mss: M3BreakEvent,
) -> tuple[bool, M1CausalSetup | None]:
    break_indices = [
        index
        for index, bar in enumerate(execution)
        if mss.break_opened_at
        <= bar.opened_at
        < mss.break_confirmed_at
    ]
    if not break_indices:
        return False, None

    first_break_index = break_indices[0]
    ob_index: int | None = None
    for index in range(first_break_index - 1, -1, -1):
        bar = execution[index]
        if bar.opened_at < crt.sweep_at:
            break
        opposing = (
            bar.close < bar.open
            if crt.side is CapitalizerSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            ob_index = index
            break
    if ob_index is None:
        return False, None

    candidates: list[tuple[int, datetime, Decimal, Decimal]] = []
    last_break_index = break_indices[-1]
    start_center = max(1, ob_index + 1)
    end_center = min(
        len(execution) - 1,
        last_break_index + 1,
    )
    for center in range(start_center, end_center):
        first = execution[center - 1]
        third = execution[center + 1]
        if third.closed_at > mss.break_confirmed_at:
            continue
        if crt.side is CapitalizerSide.LONG:
            valid = first.high < third.low
            low, high = first.high, third.low
        else:
            valid = first.low > third.high
            low, high = third.high, first.low
        if valid:
            candidates.append(
                (
                    center,
                    third.closed_at,
                    low,
                    high,
                )
            )

    if not candidates:
        return True, None

    _, formed_at, fvg_low, fvg_high = min(
        candidates,
        key=lambda item: (
            item[1],
            item[0],
        ),
    )
    departed = (
        mss.break_close > fvg_high
        if crt.side is CapitalizerSide.LONG
        else mss.break_close < fvg_low
    )
    if not departed:
        return True, None

    ob = execution[ob_index]
    retest_price = (
        fvg_high
        if crt.side is CapitalizerSide.LONG
        else fvg_low
    )
    return True, M1CausalSetup(
        ob_index=ob_index,
        ob_opened_at=ob.opened_at,
        ob_low=ob.low,
        ob_high=ob.high,
        fvg_confirmed_at=formed_at,
        fvg_low=fvg_low,
        fvg_high=fvg_high,
        retest_price=retest_price,
    )


def _find_retest(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    setup: M1CausalSetup,
    after: datetime,
) -> tuple[int, Decimal] | None:
    for index, bar in enumerate(execution):
        if bar.opened_at < after:
            continue
        if bar.low <= setup.retest_price <= bar.high:
            return index, setup.retest_price
    return None


def _target_geometry(
    *,
    crt: CRTEvent,
    entry_price: Decimal,
) -> tuple[Decimal, Decimal] | None:
    tp1 = crt.reference_eq
    tp2 = (
        crt.reference_high
        if crt.side is CapitalizerSide.LONG
        else crt.reference_low
    )
    if crt.side is CapitalizerSide.LONG:
        if not (entry_price < tp1 < tp2):
            return None
    else:
        if not (entry_price > tp1 > tp2):
            return None
    return tp1, tp2


def _lifecycle(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    entry_index: int,
    side: CapitalizerSide,
    entry_price: Decimal,
    stop_price: Decimal,
    tp1_price: Decimal,
    tp2_price: Decimal,
) -> tuple[Decimal, str, bool, bool, int, bool, datetime]:
    risk = abs(entry_price - stop_price)
    if risk <= 0:
        raise ValueError("V4 lifecycle requires positive risk")

    tp1_r = abs(tp1_price - entry_price) / risk
    tp2_r = abs(tp2_price - entry_price) / risk
    held = 0
    tp1_hit = False
    ambiguity = False
    last_close = entry_price

    for index in range(entry_index, len(execution)):
        bar = execution[index]
        held += 1
        last_close = bar.close

        active_stop = (
            entry_price
            if tp1_hit and index > entry_index
            else stop_price
        )
        stop_hit = (
            bar.low <= active_stop
            if side is CapitalizerSide.LONG
            else bar.high >= active_stop
        )
        tp1_touched = (
            bar.high >= tp1_price
            if side is CapitalizerSide.LONG
            else bar.low <= tp1_price
        )
        tp2_touched = (
            bar.high >= tp2_price
            if side is CapitalizerSide.LONG
            else bar.low <= tp2_price
        )

        if stop_hit:
            ambiguity = tp1_touched or tp2_touched
            if not tp1_hit:
                return (
                    Decimal("-1"),
                    "STOP",
                    False,
                    False,
                    held,
                    ambiguity,
                    bar.closed_at,
                )
            return (
                Decimal("0.5") * tp1_r,
                "TP1",
                True,
                False,
                held,
                ambiguity,
                bar.closed_at,
            )

        if tp2_touched:
            return (
                Decimal("0.5") * tp1_r
                + Decimal("0.5") * tp2_r,
                "TP2",
                True,
                True,
                held,
                False,
                bar.closed_at,
            )

        if tp1_touched:
            tp1_hit = True

    session_delta_r = (
        (last_close - entry_price) / risk
        if side is CapitalizerSide.LONG
        else (entry_price - last_close) / risk
    )
    if tp1_hit:
        realized = (
            Decimal("0.5") * tp1_r
            + Decimal("0.5") * max(session_delta_r, Decimal("0"))
        )
    else:
        realized = session_delta_r
    return (
        realized,
        "SESSION_EXIT",
        tp1_hit,
        False,
        held,
        ambiguity,
        execution[-1].closed_at,
    )


def _scan_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    execution: tuple[CapitalizerM1Bar, ...],
    h1: tuple[AggregatedBar, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
    buffer_price: Decimal,
    stages: Counter[str],
) -> tuple[V4Trade, ...]:
    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return ()

    results: list[V4Trade] = []
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

        ob_found, setup = _m1_causal_setup(
            execution,
            crt=crt,
            mss=mss,
        )
        if ob_found:
            stages["M1_OB_IDENTIFIED"] += 1
        if setup is None:
            stages["M1_LINKED_FVG_MISSING"] += 1
            continue
        stages["M1_LINKED_FVG_CONFIRMED"] += 1

        retest = _find_retest(
            execution,
            setup=setup,
            after=mss.break_confirmed_at,
        )
        if retest is None:
            stages["M1_FVG_RETEST_MISSING"] += 1
            continue
        entry_index, entry_price = retest
        stages["M1_FVG_RETEST"] += 1

        stop_price = (
            setup.ob_low - buffer_price
            if crt.side is CapitalizerSide.LONG
            else setup.ob_high + buffer_price
        )
        valid_stop = (
            stop_price < entry_price
            if crt.side is CapitalizerSide.LONG
            else stop_price > entry_price
        )
        if not valid_stop:
            stages["M1_OB_STOP_INVALID"] += 1
            continue

        targets = _target_geometry(
            crt=crt,
            entry_price=entry_price,
        )
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
            entry_index=entry_index,
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
            V4Trade(
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
                m3_break_close=str(mss.break_close),
                m1_ob_opened_at=setup.ob_opened_at.isoformat(),
                m1_ob_low=str(setup.ob_low),
                m1_ob_high=str(setup.ob_high),
                m1_fvg_confirmed_at=setup.fvg_confirmed_at.isoformat(),
                m1_fvg_low=str(setup.fvg_low),
                m1_fvg_high=str(setup.fvg_high),
                entry_at=execution[entry_index].opened_at.isoformat(),
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
) -> tuple[V4MarketReport, tuple[V4Trade, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("V4 replay found no native M1")

    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("V4 requires one symbol per M1 root")

    h1 = _aggregate_h1(all_bars)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_pivots = _pivots(m3)
    m5_closes = tuple(bar.closed_at for bar in m5)
    m3_closes = tuple(bar.closed_at for bar in m3)
    buffer_price = _stop_buffer(all_bars)

    execution_by_day, _ = _index_day_inputs(
        all_bars,
        session=session,
    )
    grouped_dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat()
        <= key
        < WINDOW_END.date().isoformat()
    )

    stages: Counter[str] = Counter()
    trades: list[V4Trade] = []
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

    ordered = tuple(
        sorted(
            trades,
            key=lambda item: _aware(item.entry_at),
        )
    )
    report = V4MarketReport(
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
        m1_fvg_linked=stages["M1_LINKED_FVG_CONFIRMED"],
        m1_fvg_retests=stages["M1_FVG_RETEST"],
        entries_executed=len(ordered),
        target_geometry_invalid=stages["TARGET_GEOMETRY_INVALID"],
        raw_metrics=_metrics(ordered),
        stage_counts=tuple(
            sorted(
                stages.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        buffer_price=str(buffer_price),
    )
    return report, ordered


def write_market(
    report: V4MarketReport,
    trades: tuple[V4Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-crt-h1-m3-m1-1y-v4"
    (output / f"{stem}.json").write_text(
        json.dumps(
            asdict(report),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for trade in trades:
            handle.write(
                json.dumps(
                    asdict(trade),
                    sort_keys=True,
                )
                + "\n"
            )


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-crt-h1-m3-m1-1y-v4.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"V4 matrix requires 9 reports, got {len(paths)}"
        )
    reports: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("identity") != IDENTITY:
            raise ValueError("unexpected V4 market report")
        reports.append(dict(raw))
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("V4 universe mismatch")
    return sorted(
        reports,
        key=lambda item: str(item["symbol"]),
    )


def _load_trades(root: Path) -> tuple[V4Trade, ...]:
    rows: list[V4Trade] = []
    for path in sorted(
        root.rglob(
            "capitalizer-*-crt-h1-m3-m1-1y-v4-trades.jsonl"
        )
    ):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V4Trade(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                _aware(item.entry_at),
                item.symbol,
            ),
        )
    )


def _portfolio_max3(
    trades: tuple[V4Trade, ...],
) -> tuple[V4Trade, ...]:
    grouped: dict[str, list[V4Trade]] = defaultdict(list)
    for trade in trades:
        grouped[
            f"{trade.session}:{trade.operating_date}"
        ].append(trade)
    selected: list[V4Trade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (
                _aware(item.entry_at),
                item.symbol,
            ),
        )
        selected.extend(
            ordered[:MAX_EXECUTIONS_PER_SESSION]
        )
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                _aware(item.entry_at),
                item.symbol,
            ),
        )
    )


def _monthly_counts(
    trades: tuple[V4Trade, ...],
) -> dict[str, int]:
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
            trade
            for trade in raw
            if trade.session == session.value
        )
        session_max3 = tuple(
            trade
            for trade in max3
            if trade.session == session.value
        )
        raw_value = _metrics(session_raw)
        max3_value = _metrics(session_max3)
        per_session[session.value] = {
            "raw_trades": len(session_raw),
            "raw_metrics": (
                None
                if raw_value is None
                else asdict(raw_value)
            ),
            "max3_trades": len(session_max3),
            "max3_metrics": (
                None
                if max3_value is None
                else asdict(max3_value)
            ),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "architecture": (
            "H1_N_N1_CRT_TO_M5_CLOSEBACK_TO_M3_LAST_PIVOT_MSS_"
            "TO_M1_CAUSAL_OB_FVG_RETEST"
        ),
        "architecture_predeclared": True,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "h1_candles_evaluated": sum(
            int(item["h1_candles_evaluated"])
            for item in reports
        ),
        "h1_sweeps_detected": sum(
            int(item["h1_sweeps_detected"])
            for item in reports
        ),
        "m5_closebacks_confirmed": sum(
            int(item["m5_closebacks_confirmed"])
            for item in reports
        ),
        "m3_mss_confirmed": sum(
            int(item["m3_mss_confirmed"])
            for item in reports
        ),
        "m1_ob_identified": sum(
            int(item["m1_ob_identified"])
            for item in reports
        ),
        "m1_fvg_linked": sum(
            int(item["m1_fvg_linked"])
            for item in reports
        ),
        "m1_fvg_retests": sum(
            int(item["m1_fvg_retests"])
            for item in reports
        ),
        "raw_trades": len(raw),
        "raw_metrics": (
            None
            if raw_metrics is None
            else asdict(raw_metrics)
        ),
        "max3_selected_trades": len(max3),
        "max3_metrics": (
            None
            if max3_metrics is None
            else asdict(max3_metrics)
        ),
        "monthly_max3_trades": _monthly_counts(max3),
        "days_with_any_trade": len(
            {trade.operating_date for trade in max3}
        ),
        "per_session": per_session,
        "markets": reports,
        "raw_stop_exits": sum(
            trade.exit_reason == "STOP" for trade in raw
        ),
        "raw_tp1_exits": sum(
            trade.exit_reason == "TP1" for trade in raw
        ),
        "raw_tp2_exits": sum(
            trade.exit_reason == "TP2" for trade in raw
        ),
        "raw_session_exits": sum(
            trade.exit_reason == "SESSION_EXIT"
            for trade in raw
        ),
        "raw_tp1_hits": sum(
            trade.tp1_hit for trade in raw
        ),
        "raw_tp2_hits": sum(
            trade.tp2_hit for trade in raw
        ),
        "max3_stop_exits": sum(
            trade.exit_reason == "STOP" for trade in max3
        ),
        "max3_tp1_exits": sum(
            trade.exit_reason == "TP1" for trade in max3
        ),
        "max3_tp2_exits": sum(
            trade.exit_reason == "TP2" for trade in max3
        ),
        "max3_session_exits": sum(
            trade.exit_reason == "SESSION_EXIT"
            for trade in max3
        ),
        "max3_tp1_hits": sum(
            trade.tp1_hit for trade in max3
        ),
        "max3_tp2_hits": sum(
            trade.tp2_hit for trade in max3
        ),
        "entry_identity": ENTRY_IDENTITY,
        "stop_identity": STOP_IDENTITY,
        "target_identity": TARGET_IDENTITY,
        "reference_rule": "IMMEDIATELY_PREVIOUS_COMPLETED_H1",
        "m3_swing_rule": "LAST_3_CANDLE_PIVOT_FORMED_PRE_SWEEP",
        "m3_cisd_required": False,
        "m3_body_threshold_required": False,
        "m3_atr_threshold_required": False,
        "m1_retest_required": True,
        "m1_ce_fallback_allowed": False,
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


def write_matrix(
    report: dict[str, Any],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-crt-h1-m3-m1-1y-v4.json"
    )
    path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )
    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[
            item.value
            for item in CapitalizerSession
        ],
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
        write_market(
            report,
            trades,
            args.output,
        )
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

    matrix_report = build_matrix(args.input_root)
    write_matrix(
        matrix_report,
        args.output,
    )
    print(
        json.dumps(
            matrix_report,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
