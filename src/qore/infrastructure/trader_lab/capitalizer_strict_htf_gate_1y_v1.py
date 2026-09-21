"""Strict hierarchical 1Y replay for QORE Capitalizer.

Research question
-----------------
What happens when M1 loses all authority to originate a trade and can only execute
after the higher-timeframe chain has causally opened the gate?

Frozen experimental chain:
    latest completed H1 candle must itself carry a valid C2/C3 bias event
    -> prior-session significant liquidity sweep with close back through the level
    -> M15 close through an opposing confirmed swing
    -> M5 close through an opposing confirmed swing
    -> M1 directional displacement + close through an opposing M1 pivot
    -> M1 FVG
    -> first subsequent causal touch of FVG consequent encroachment (50%)
    -> entry

Risk/lifecycle:
    stop = protected swing from the M5 structural confirmation
    target = fixed 2R
    same-session lifecycle
    same-minute stop/target ambiguity = STOP_FIRST
    MAX3/session is a ceiling at portfolio aggregation, never a quota.

Timing:
    ASIA execution window: 20:00-00:00 New York
    LONDON execution window: 02:00-05:00 New York
    NEW_YORK execution window: 08:30-11:00 New York

Reference liquidity:
    ASIA sweeps the previous completed New York 08:30-16:00 range.
    LONDON sweeps the completed Asia 20:00-00:00 range.
    NEW_YORK sweeps the completed London 02:00-05:00 range.

No body-ratio, ATR, CE-rejection, premium/discount, order-block, or fitted
threshold gate is introduced here. Those remain falsification variables rather
than invented doctrine.

Window: [2025-09-17, 2026-09-17)
Research only. No certification, promotion, live or real-capital authority.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
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
    HTFBiasEvent,
    _aggregate_h1,
    _build_htf_bias_events,
)
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    WINDOW_END,
    WINDOW_START,
    ICTReplayMetrics,
    _aware,
    _lifecycle,
    _operating_date,
    _significant_displacement,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_CAPITALIZER_STRICT_HTF_GATE_1Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STRICT_HTF_GATE_1Y_MATRIX_V1"
ENTRY_IDENTITY = "H1_C2C3__PRIOR_SESSION_SWEEP__M15_BREAK__M5_BREAK__M1_MSS_FVG_CE"
STOP_IDENTITY = "M5_PROTECTED_SWING"
TARGET_IDENTITY = "FIXED_2R"
LOOKBACK_START = WINDOW_START - timedelta(days=14)
NEW_YORK = ZoneInfo("America/New_York")
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
class TFBar:
    opened_at: datetime
    closed_at: datetime
    source: CapitalizerSourceBar


@dataclass(frozen=True, slots=True)
class Pivot:
    occurred_at: datetime
    confirmed_at: datetime
    price: Decimal
    kind: str


@dataclass(frozen=True, slots=True)
class StructureEvent:
    confirmed_at: datetime
    break_price: Decimal
    protected_swing_price: Decimal
    timeframe: str


@dataclass(frozen=True, slots=True)
class ReferenceLiquidity:
    opened_at: datetime
    closed_at: datetime
    high: Decimal
    low: Decimal
    source: str


@dataclass(frozen=True, slots=True)
class StrictTrade:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_bias_confirmed_at: str
    h1_closure_kind: str
    h1_poi_kind: str
    reference_liquidity_source: str
    reference_high: str
    reference_low: str
    sweep_at: str
    sweep_level: str
    sweep_extreme: str
    m15_confirmed_at: str
    m15_break_price: str
    m15_protected_swing_price: str
    m5_confirmed_at: str
    m5_break_price: str
    m5_protected_swing_price: str
    m1_displacement_at: str
    m1_mss_level: str
    m1_fvg_confirmed_at: str
    m1_fvg_low: str
    m1_fvg_high: str
    m1_ce_price: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    target_price: str
    planned_reward_r: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    same_minute_stop_target_ambiguity: bool
    entry_definition: str = ENTRY_IDENTITY
    stop_definition: str = STOP_IDENTITY
    target_definition: str = TARGET_IDENTITY
    m1_originated_trade: bool = False
    daily_driver_used: bool = False
    order_block_required: bool = False
    fitted_threshold_used: bool = False
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class StrictMarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    operating_sessions_scanned: int
    sessions_with_reference_liquidity: int
    h1_gate_passes: int
    prior_session_sweeps: int
    m15_structure_passes: int
    m5_structure_passes: int
    m1_mss_passes: int
    m1_fvg_passes: int
    raw_entries: int
    raw_metrics: ICTReplayMetrics | None
    raw_stop_exits: int
    raw_target_exits: int
    raw_session_exits: int
    sessions_with_entry: int
    max_entries_one_market_session: int
    stage_counts: tuple[tuple[str, int], ...]
    max3_is_ceiling_not_quota: bool = True
    methodology_research_only: bool = True
    daily_driver_used: bool = False
    m1_can_originate_trade: bool = False
    body_atr_threshold_gate_used: bool = False
    premium_discount_gate_used: bool = False
    order_block_required: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _aggregate_tf(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    minutes: int,
) -> tuple[TFBar, ...]:
    grouped: dict[tuple[int, int, int, int, int, int], list[CapitalizerM1Bar]] = (
        defaultdict(list)
    )
    for bar in bars:
        local = bar.opened_at.astimezone(NEW_YORK)
        offset = local.utcoffset()
        if offset is None:
            raise ValueError("NY-local M1 bar requires UTC offset")
        floored = (local.minute // minutes) * minutes
        grouped[
            (
                local.year,
                local.month,
                local.day,
                local.hour,
                floored,
                int(offset.total_seconds()),
            )
        ].append(bar)

    result: list[TFBar] = []
    minimum = max(1, minutes * 3 // 4)
    for key in sorted(grouped):
        chunk = sorted(grouped[key], key=lambda item: item.opened_at)
        if len(chunk) < minimum:
            continue
        result.append(
            TFBar(
                opened_at=chunk[0].opened_at,
                closed_at=chunk[-1].closed_at,
                source=CapitalizerSourceBar(
                    open=chunk[0].open,
                    high=max(item.high for item in chunk),
                    low=min(item.low for item in chunk),
                    close=chunk[-1].close,
                ),
            )
        )
    return tuple(result)


def _pivots(bars: tuple[TFBar, ...]) -> tuple[Pivot, ...]:
    result: list[Pivot] = []
    for center in range(1, len(bars) - 1):
        left, mid, right = bars[center - 1], bars[center], bars[center + 1]
        if mid.source.high > left.source.high and mid.source.high > right.source.high:
            result.append(
                Pivot(
                    occurred_at=mid.opened_at,
                    confirmed_at=right.closed_at,
                    price=mid.source.high,
                    kind="HIGH",
                )
            )
        if mid.source.low < left.source.low and mid.source.low < right.source.low:
            result.append(
                Pivot(
                    occurred_at=mid.opened_at,
                    confirmed_at=right.closed_at,
                    price=mid.source.low,
                    kind="LOW",
                )
            )
    return tuple(sorted(result, key=lambda item: item.confirmed_at))


def _m1_pivots(bars: tuple[CapitalizerM1Bar, ...]) -> tuple[Pivot, ...]:
    result: list[Pivot] = []
    for center in range(1, len(bars) - 1):
        left, mid, right = bars[center - 1], bars[center], bars[center + 1]
        if mid.high > left.high and mid.high > right.high:
            result.append(Pivot(mid.opened_at, right.closed_at, mid.high, "HIGH"))
        if mid.low < left.low and mid.low < right.low:
            result.append(Pivot(mid.opened_at, right.closed_at, mid.low, "LOW"))
    return tuple(sorted(result, key=lambda item: item.confirmed_at))


def _window_local(
    operating_day: date,
    *,
    session: CapitalizerSession,
) -> tuple[datetime, datetime]:
    if session is CapitalizerSession.ASIA:
        start = datetime.combine(operating_day, time(20, 0), tzinfo=NEW_YORK)
        return start, start + timedelta(hours=4)
    if session is CapitalizerSession.LONDON:
        start = datetime.combine(operating_day, time(2, 0), tzinfo=NEW_YORK)
        return start, start + timedelta(hours=3)
    start = datetime.combine(operating_day, time(8, 30), tzinfo=NEW_YORK)
    return start, start + timedelta(hours=2, minutes=30)


def _reference_window_local(
    operating_day: date,
    *,
    session: CapitalizerSession,
) -> tuple[datetime, datetime, str]:
    if session is CapitalizerSession.ASIA:
        start = datetime.combine(operating_day, time(8, 30), tzinfo=NEW_YORK)
        end = datetime.combine(operating_day, time(16, 0), tzinfo=NEW_YORK)
        return start, end, "PREVIOUS_COMPLETED_NEW_YORK_RANGE"
    if session is CapitalizerSession.LONDON:
        prior = operating_day - timedelta(days=1)
        start = datetime.combine(prior, time(20, 0), tzinfo=NEW_YORK)
        end = datetime.combine(operating_day, time(0, 0), tzinfo=NEW_YORK)
        return start, end, "COMPLETED_ASIA_RANGE"
    start = datetime.combine(operating_day, time(2, 0), tzinfo=NEW_YORK)
    end = datetime.combine(operating_day, time(5, 0), tzinfo=NEW_YORK)
    return start, end, "COMPLETED_LONDON_RANGE"


def _reference_liquidity(
    all_bars: tuple[CapitalizerM1Bar, ...],
    *,
    operating_day: date,
    session: CapitalizerSession,
) -> ReferenceLiquidity | None:
    start_local, end_local, source = _reference_window_local(
        operating_day,
        session=session,
    )
    chunk = tuple(
        bar
        for bar in all_bars
        if start_local <= bar.opened_at.astimezone(NEW_YORK) < end_local
    )
    if len(chunk) < 30:
        return None
    return ReferenceLiquidity(
        opened_at=chunk[0].opened_at,
        closed_at=chunk[-1].closed_at,
        high=max(item.high for item in chunk),
        low=min(item.low for item in chunk),
        source=source,
    )


def _execution_bars(
    all_bars: tuple[CapitalizerM1Bar, ...],
    *,
    operating_day: date,
    session: CapitalizerSession,
) -> tuple[CapitalizerM1Bar, ...]:
    start_local, end_local = _window_local(operating_day, session=session)
    return tuple(
        bar
        for bar in all_bars
        if start_local <= bar.opened_at.astimezone(NEW_YORK) < end_local
    )


def _latest_completed_h1(
    h1: tuple[AggregatedBar, ...],
    moment: datetime,
) -> AggregatedBar | None:
    available = [bar for bar in h1 if bar.closed_at <= moment]
    return None if not available else available[-1]


def _immediate_h1_bias(
    h1: tuple[AggregatedBar, ...],
    bias_events: tuple[HTFBiasEvent, ...],
    moment: datetime,
) -> HTFBiasEvent | None:
    latest_bar = _latest_completed_h1(h1, moment)
    if latest_bar is None:
        return None
    matching = [
        event
        for event in bias_events
        if event.confirmed_at == latest_bar.closed_at
        and event.confirmed_at <= moment
    ]
    if not matching:
        return None
    return matching[-1]


def _side_from_bias(bias: HTFBiasEvent) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if bias.direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSide.SHORT
    )


def _sweep_confirmed(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    reference: ReferenceLiquidity,
) -> bool:
    if side is CapitalizerSide.LONG:
        return bar.low < reference.low and bar.close > reference.low
    return bar.high > reference.high and bar.close < reference.high


def _sweep_level(
    *,
    side: CapitalizerSide,
    reference: ReferenceLiquidity,
) -> Decimal:
    return reference.low if side is CapitalizerSide.LONG else reference.high


def _sweep_extreme(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
) -> Decimal:
    return bar.low if side is CapitalizerSide.LONG else bar.high


def _latest_pivot(
    pivots: tuple[Pivot, ...],
    *,
    before: datetime,
    kind: str,
) -> Pivot | None:
    available = [
        pivot
        for pivot in pivots
        if pivot.confirmed_at < before and pivot.kind == kind
    ]
    return None if not available else available[-1]


def _find_structure_event(
    bars: tuple[TFBar, ...],
    pivots: tuple[Pivot, ...],
    *,
    after: datetime,
    before: datetime,
    side: CapitalizerSide,
    timeframe: str,
) -> StructureEvent | None:
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    protect_kind = "LOW" if side is CapitalizerSide.LONG else "HIGH"

    for bar in bars:
        if not (after < bar.closed_at <= before):
            continue
        break_pivot = _latest_pivot(
            pivots,
            before=bar.opened_at,
            kind=break_kind,
        )
        protected = _latest_pivot(
            pivots,
            before=bar.opened_at,
            kind=protect_kind,
        )
        if break_pivot is None or protected is None:
            continue
        broke = (
            bar.source.close > break_pivot.price
            if side is CapitalizerSide.LONG
            else bar.source.close < break_pivot.price
        )
        if not broke:
            continue
        return StructureEvent(
            confirmed_at=bar.closed_at,
            break_price=break_pivot.price,
            protected_swing_price=protected.price,
            timeframe=timeframe,
        )
    return None


def _latest_m1_pivot(
    pivots: tuple[Pivot, ...],
    *,
    before: datetime,
    side: CapitalizerSide,
) -> Pivot | None:
    kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    return _latest_pivot(pivots, before=before, kind=kind)


def _m1_entry_after_structure(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    m1_pivots: tuple[Pivot, ...],
    after: datetime,
    side: CapitalizerSide,
    stop_price: Decimal,
    stages: Counter[str],
) -> tuple[
    int,
    Decimal,
    Decimal,
    Decimal,
    datetime,
    Decimal,
] | None:
    start_index = bisect.bisect_right(
        tuple(item.opened_at for item in execution),
        after,
    )
    for index in range(max(1, start_index), len(execution) - 1):
        displacement = execution[index]
        if not _significant_displacement(displacement, side=side):
            continue
        mss = _latest_m1_pivot(
            m1_pivots,
            before=displacement.opened_at,
            side=side,
        )
        if mss is None:
            continue
        closed_through = (
            displacement.close > mss.price
            if side is CapitalizerSide.LONG
            else displacement.close < mss.price
        )
        if not closed_through:
            continue
        stages["M1_MSS_AFTER_HTF_GATE"] += 1

        first = execution[index - 1]
        third = execution[index + 1]
        if side is CapitalizerSide.LONG:
            valid_fvg = first.high < third.low
            fvg_low, fvg_high = first.high, third.low
        else:
            valid_fvg = first.low > third.high
            fvg_low, fvg_high = third.high, first.low
        if not valid_fvg:
            continue
        stages["M1_FVG_AFTER_HTF_GATE"] += 1
        ce = (fvg_low + fvg_high) / Decimal("2")

        for entry_index in range(index + 2, len(execution)):
            bar = execution[entry_index]
            touched = bar.low <= ce <= bar.high
            if not touched:
                continue
            valid_stop = (
                stop_price < ce
                if side is CapitalizerSide.LONG
                else stop_price > ce
            )
            if not valid_stop:
                stages["M5_PROTECTED_SWING_INVALID_GEOMETRY"] += 1
                return None
            return (
                entry_index,
                ce,
                fvg_low,
                fvg_high,
                third.closed_at,
                mss.price,
            )
    return None


def _metrics(trades: tuple[StrictTrade, ...]) -> ICTReplayMetrics | None:
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
        session_exits=sum(item.exit_reason == "SESSION_EXIT" for item in ordered),
        ambiguous_stop_first_exits=sum(
            item.same_minute_stop_target_ambiguity for item in ordered
        ),
    )


def _scan_operating_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1: tuple[AggregatedBar, ...],
    bias_events: tuple[HTFBiasEvent, ...],
    m15: tuple[TFBar, ...],
    m15_pivots: tuple[Pivot, ...],
    m5: tuple[TFBar, ...],
    m5_pivots: tuple[Pivot, ...],
    stages: Counter[str],
) -> tuple[StrictTrade, ...]:
    reference = _reference_liquidity(
        all_bars,
        operating_day=operating_day,
        session=session,
    )
    if reference is None:
        stages["REFERENCE_LIQUIDITY_UNAVAILABLE"] += 1
        return ()
    stages["REFERENCE_LIQUIDITY_AVAILABLE"] += 1

    execution = _execution_bars(
        all_bars,
        operating_day=operating_day,
        session=session,
    )
    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return ()
    m1_pivots = _m1_pivots(execution)

    results: list[StrictTrade] = []
    cursor = 2
    while cursor < len(execution) and len(results) < MAX_EXECUTIONS_PER_SESSION:
        sweep_index: int | None = None
        bias: HTFBiasEvent | None = None
        side: CapitalizerSide | None = None
        for index in range(cursor, len(execution)):
            candidate_bias = _immediate_h1_bias(
                h1,
                bias_events,
                execution[index].opened_at,
            )
            if candidate_bias is None:
                continue
            stages["H1_GATE_PASS"] += 1
            candidate_side = _side_from_bias(candidate_bias)
            if _sweep_confirmed(
                execution[index],
                side=candidate_side,
                reference=reference,
            ):
                sweep_index = index
                bias = candidate_bias
                side = candidate_side
                break
        if sweep_index is None or bias is None or side is None:
            stages["NO_CAUSAL_SWEEP_AFTER_H1_GATE"] += 1
            break
        sweep_bar = execution[sweep_index]
        stages["PRIOR_SESSION_SWEEP"] += 1

        window_end = execution[-1].closed_at
        m15_event = _find_structure_event(
            m15,
            m15_pivots,
            after=sweep_bar.closed_at,
            before=window_end,
            side=side,
            timeframe="M15",
        )
        if m15_event is None:
            stages["M15_STRUCTURE_MISSING"] += 1
            cursor = sweep_index + 1
            continue
        stages["M15_STRUCTURE_PASS"] += 1

        m5_event = _find_structure_event(
            m5,
            m5_pivots,
            after=m15_event.confirmed_at,
            before=window_end,
            side=side,
            timeframe="M5",
        )
        if m5_event is None:
            stages["M5_STRUCTURE_MISSING"] += 1
            cursor = sweep_index + 1
            continue
        stages["M5_STRUCTURE_PASS"] += 1

        setup = _m1_entry_after_structure(
            execution,
            m1_pivots=m1_pivots,
            after=m5_event.confirmed_at,
            side=side,
            stop_price=m5_event.protected_swing_price,
            stages=stages,
        )
        if setup is None:
            stages["M1_EXECUTION_MISSING"] += 1
            cursor = sweep_index + 1
            continue

        (
            entry_index,
            entry_price,
            fvg_low,
            fvg_high,
            fvg_confirmed_at,
            m1_mss_level,
        ) = setup
        risk = abs(entry_price - m5_event.protected_swing_price)
        if risk <= 0:
            stages["NONPOSITIVE_RISK"] += 1
            cursor = entry_index + 1
            continue
        target = (
            entry_price + Decimal("2") * risk
            if side is CapitalizerSide.LONG
            else entry_price - Decimal("2") * risk
        )
        realized, reason, held, ambiguous, exit_at = _lifecycle(
            execution,
            entry_index=entry_index,
            side=side,
            entry_price=entry_price,
            stop_price=m5_event.protected_swing_price,
            target_price=target,
        )
        stages["M1_CE_ENTRY"] += 1
        results.append(
            StrictTrade(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=side.value,
                h1_bias_confirmed_at=bias.confirmed_at.isoformat(),
                h1_closure_kind=bias.closure_kind,
                h1_poi_kind=bias.poi_kind,
                reference_liquidity_source=reference.source,
                reference_high=str(reference.high),
                reference_low=str(reference.low),
                sweep_at=sweep_bar.opened_at.isoformat(),
                sweep_level=str(_sweep_level(side=side, reference=reference)),
                sweep_extreme=str(_sweep_extreme(sweep_bar, side=side)),
                m15_confirmed_at=m15_event.confirmed_at.isoformat(),
                m15_break_price=str(m15_event.break_price),
                m15_protected_swing_price=str(m15_event.protected_swing_price),
                m5_confirmed_at=m5_event.confirmed_at.isoformat(),
                m5_break_price=str(m5_event.break_price),
                m5_protected_swing_price=str(m5_event.protected_swing_price),
                m1_displacement_at=execution[
                    max(0, entry_index - 2)
                ].closed_at.isoformat(),
                m1_mss_level=str(m1_mss_level),
                m1_fvg_confirmed_at=fvg_confirmed_at.isoformat(),
                m1_fvg_low=str(fvg_low),
                m1_fvg_high=str(fvg_high),
                m1_ce_price=str(entry_price),
                entry_at=execution[entry_index].opened_at.isoformat(),
                exit_at=exit_at.isoformat(),
                entry_price=str(entry_price),
                stop_price=str(m5_event.protected_swing_price),
                target_price=str(target),
                planned_reward_r="2",
                realized_gross_r=str(realized),
                exit_reason=reason,
                m1_bars_held=held,
                same_minute_stop_target_ambiguity=ambiguous,
            )
        )
        exit_index = next(
            (
                index
                for index in range(entry_index, len(execution))
                if execution[index].closed_at >= exit_at
            ),
            len(execution) - 1,
        )
        cursor = exit_index + 1

    return tuple(results)


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[StrictMarketReport, tuple[StrictTrade, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("strict HTF replay found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("strict HTF replay requires one symbol per M1 root")

    h1 = _aggregate_h1(all_bars)
    bias_events = _build_htf_bias_events(h1)
    m15 = _aggregate_tf(all_bars, minutes=15)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m15_pivots = _pivots(m15)
    m5_pivots = _pivots(m5)

    grouped_dates = sorted(
        {
            _operating_date(bar.opened_at, session)
            for bar in all_bars
            if WINDOW_START <= bar.opened_at < WINDOW_END
        }
    )
    stages: Counter[str] = Counter()
    trades: list[StrictTrade] = []
    per_day: Counter[str] = Counter()
    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        produced = _scan_operating_day(
            symbol=symbol,
            session=session,
            operating_day=operating_day,
            all_bars=all_bars,
            h1=h1,
            bias_events=bias_events,
            m15=m15,
            m15_pivots=m15_pivots,
            m5=m5,
            m5_pivots=m5_pivots,
            stages=stages,
        )
        trades.extend(produced)
        per_day[value] += len(produced)

    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    report = StrictMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        operating_sessions_scanned=len(grouped_dates),
        sessions_with_reference_liquidity=stages["REFERENCE_LIQUIDITY_AVAILABLE"],
        h1_gate_passes=stages["H1_GATE_PASS"],
        prior_session_sweeps=stages["PRIOR_SESSION_SWEEP"],
        m15_structure_passes=stages["M15_STRUCTURE_PASS"],
        m5_structure_passes=stages["M5_STRUCTURE_PASS"],
        m1_mss_passes=stages["M1_MSS_AFTER_HTF_GATE"],
        m1_fvg_passes=stages["M1_FVG_AFTER_HTF_GATE"],
        raw_entries=len(ordered),
        raw_metrics=_metrics(ordered),
        raw_stop_exits=sum(item.exit_reason == "STOP" for item in ordered),
        raw_target_exits=sum(item.exit_reason == "TARGET" for item in ordered),
        raw_session_exits=sum(item.exit_reason == "SESSION_EXIT" for item in ordered),
        sessions_with_entry=sum(count > 0 for count in per_day.values()),
        max_entries_one_market_session=max(per_day.values(), default=0),
        stage_counts=tuple(
            sorted(stages.items(), key=lambda item: (-item[1], item[0]))
        ),
    )
    return report, ordered


def write_market(
    report: StrictMarketReport,
    trades: tuple[StrictTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-strict-htf-gate-1y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-strict-htf-gate-1y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"strict HTF matrix requires 9 reports, got {len(paths)}")
    reports: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("identity") != IDENTITY:
            raise ValueError("unexpected strict HTF market report")
        reports.append(dict(raw))
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("strict HTF universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def _load_trades(root: Path) -> tuple[StrictTrade, ...]:
    rows: list[StrictTrade] = []
    for path in sorted(root.rglob("capitalizer-*-strict-htf-gate-1y-v1-trades.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(StrictTrade(**json.loads(line)))
    return tuple(sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol)))


def _portfolio_max3(trades: tuple[StrictTrade, ...]) -> tuple[StrictTrade, ...]:
    grouped: dict[str, list[StrictTrade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)
    selected: list[StrictTrade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol)))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = _portfolio_max3(raw)

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        session_raw = tuple(item for item in raw if item.session == session.value)
        session_max3 = tuple(item for item in max3 if item.session == session.value)
        per_session[session.value] = {
            "raw_trades": len(session_raw),
            "raw_metrics": (
                None if (value := _metrics(session_raw)) is None else asdict(value)
            ),
            "max3_trades": len(session_max3),
            "max3_metrics": (
                None if (value := _metrics(session_max3)) is None else asdict(value)
            ),
        }

    raw_metrics = _metrics(raw)
    max3_metrics = _metrics(max3)
    return {
        "identity": MATRIX_IDENTITY,
        "entry_identity": ENTRY_IDENTITY,
        "stop_identity": STOP_IDENTITY,
        "target_identity": TARGET_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "raw_trades": len(raw),
        "raw_metrics": None if raw_metrics is None else asdict(raw_metrics),
        "raw_stop_exits": sum(item.exit_reason == "STOP" for item in raw),
        "raw_target_exits": sum(item.exit_reason == "TARGET" for item in raw),
        "raw_session_exits": sum(item.exit_reason == "SESSION_EXIT" for item in raw),
        "max3_selected_trades": len(max3),
        "max3_metrics": None if max3_metrics is None else asdict(max3_metrics),
        "max3_stop_exits": sum(item.exit_reason == "STOP" for item in max3),
        "max3_target_exits": sum(item.exit_reason == "TARGET" for item in max3),
        "max3_session_exits": sum(item.exit_reason == "SESSION_EXIT" for item in max3),
        "h1_gate_passes": sum(int(item["h1_gate_passes"]) for item in reports),
        "prior_session_sweeps": sum(
            int(item["prior_session_sweeps"]) for item in reports
        ),
        "m15_structure_passes": sum(
            int(item["m15_structure_passes"]) for item in reports
        ),
        "m5_structure_passes": sum(
            int(item["m5_structure_passes"]) for item in reports
        ),
        "m1_mss_passes": sum(int(item["m1_mss_passes"]) for item in reports),
        "m1_fvg_passes": sum(int(item["m1_fvg_passes"]) for item in reports),
        "per_session": per_session,
        "markets": reports,
        "max3_is_ceiling_not_quota": True,
        "methodology_research_only": True,
        "daily_driver_used": False,
        "m1_can_originate_trade": False,
        "body_atr_threshold_gate_used": False,
        "premium_discount_gate_used": False,
        "order_block_required": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-strict-htf-gate-1y-matrix-v1.json"
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
        market_report, trades = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(market_report, trades, args.output)
        print(
            json.dumps(
                {
                    "symbol": market_report.symbol,
                    "session": market_report.session,
                    "trades": market_report.raw_entries,
                    "pf": (
                        None
                        if market_report.raw_metrics is None
                        else market_report.raw_metrics.profit_factor
                    ),
                    "stops": market_report.raw_stop_exits,
                    "targets": market_report.raw_target_exits,
                },
                sort_keys=True,
            )
        )
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
