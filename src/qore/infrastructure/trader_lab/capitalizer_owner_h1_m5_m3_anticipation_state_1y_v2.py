"""QORE Capitalizer H1-M5-M3 anticipation-state replay V2.

Owner-frozen five-change experiment:
    H1 bias
    -> liquidity sweep activates persistent session state
    -> M5 CISD + MSS
    -> H1 anticipation T-Spot (running H1 EQ to previous H1 extreme)
    -> M3 trigger inside that H1 window
    -> priority: IFVG, CISD, OB+FVG, simple FVG
    -> IFVG/CISD enter on trigger close; FVG uses CE; OB+FVG may use retest
    -> entry must occur before the next H1 open
    -> stop = M5 protected swing
    -> target = fixed 2R OR next H1-open time exit
    -> same-session hard lifecycle / MAX3 ceiling

The sweep is a session state, not a per-trade gate.
M1 is intrabar evidence only and cannot originate a trade.
No M15 gate. No mandatory M3 MSS. No outcome-aware selection.
Window: [2025-09-17, 2026-09-17)
Research only. No certification, promotion, live, or real-capital authority.
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
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    ReferenceLiquidity,
    StructureEvent,
    TFBar,
    _aggregate_tf,
    _find_structure_event,
    _immediate_h1_bias,
    _index_day_inputs,
    _pivots,
    _side_from_bias,
    _sweep_confirmed,
    _sweep_extreme,
    _sweep_level,
)

IDENTITY = "QORE_CAPITALIZER_OWNER_H1_M5_M3_ANTICIPATION_STATE_ANTICIPATION_STATE_1Y_V2"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_"
    "OWNER_H1_M5_M3_ANTICIPATION_STATE_1Y_V2"
)
ENTRY_IDENTITY = (
    "H1_BIAS__SWEEP_SESSION_STATE__M5_CISD_MSS__"
    "H1_ANTICIPATION_TSPOT__M3_IFVG_CISD_OBFVG_FVG"
)
STOP_IDENTITY = "M5_PROTECTED_SWING"
TARGET_IDENTITY = "FIXED_2R_OR_SAME_H1_CLOSE"
PARENT_STRUCTURE_TIMEFRAME = "M5"
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
class AnticipationTrade:
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
    m5_confirmed_at: str
    m5_break_price: str
    m5_protected_swing_price: str
    m5_cisd_confirmed_at: str
    m5_cisd_boundary: str
    h1_tspot_low: str
    h1_tspot_high: str
    h1_tspot_defined_at: str
    h1_trigger_deadline: str
    m3_trigger_at: str
    m3_trigger_kind: str
    m3_cisd_boundary: str | None
    m3_fvg_confirmed_at: str
    m3_fvg_low: str
    m3_fvg_high: str
    m3_entry_mode: str
    m3_order_block_low: str | None
    m3_order_block_high: str | None
    m3_entry_reference_price: str
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
    sweep_state_persistent: bool = True
    tspot_definition: str = "RUNNING_H1_EQ_TO_PREVIOUS_H1_EXTREME"
    trigger_deadline_definition: str = "SAME_H1_CLOSE"
    parent_structure_timeframe: str = PARENT_STRUCTURE_TIMEFRAME
    m15_gate_required: bool = False
    entry_timeframe: str = "M3"
    m5_cisd_required: bool = True
    m5_mss_required: bool = True
    m3_mss_required: bool = False
    m3_trigger_logic: str = "IFVG_THEN_CISD_THEN_OBFVG_THEN_FVG"
    entry_mode_logic: str = "TRIGGER_CLOSE_OR_FVG_CE_OR_OBFVG_RETEST"
    time_exit: str = "SAME_H1_CLOSE"
    m1_intrabar_only: bool = True
    m1_originated_trade: bool = False
    daily_driver_used: bool = False
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class AnticipationMarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    operating_sessions_scanned: int
    sessions_with_reference_liquidity: int
    sessions_with_h1_bias: int
    h1_gate_passes: int
    prior_session_sweeps: int
    sweep_state_activations: int
    m5_structure_passes: int
    m5_cisd_passes: int
    m5_mss_passes: int
    h1_tspot_definitions: int
    m3_ifvg_triggers: int
    m3_cisd_triggers: int
    m3_ob_fvg_triggers: int
    m3_simple_fvg_triggers: int
    m3_ob_fvg_entries: int
    m3_ce_entries: int
    m3_close_entries: int
    raw_entries: int
    raw_metrics: ICTReplayMetrics | None
    raw_stop_exits: int
    raw_target_exits: int
    raw_session_exits: int
    raw_time_exits: int
    sessions_with_entry: int
    max_entries_one_market_session: int
    stage_counts: tuple[tuple[str, int], ...]
    parent_structure_timeframe: str = PARENT_STRUCTURE_TIMEFRAME
    m15_gate_required: bool = False
    architecture_predeclared: bool = True
    max3_is_ceiling_not_quota: bool = True
    methodology_research_only: bool = True
    sweep_state_persistent: bool = True
    tspot_definition: str = "RUNNING_H1_EQ_TO_PREVIOUS_H1_EXTREME"
    trigger_deadline_definition: str = "SAME_H1_CLOSE"
    daily_driver_used: bool = False
    entry_timeframe: str = "M3"
    m5_cisd_required: bool = True
    m5_mss_required: bool = True
    m3_mss_required: bool = False
    m3_trigger_logic: str = "IFVG_THEN_CISD_THEN_OBFVG_THEN_FVG"
    entry_mode_logic: str = "TRIGGER_CLOSE_OR_FVG_CE_OR_OBFVG_RETEST"
    time_exit: str = "SAME_H1_CLOSE"
    m1_intrabar_only: bool = True
    m1_can_originate_trade: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _find_m5_parent_structure(
    bars: tuple[TFBar, ...],
    pivots: tuple[Pivot, ...],
    *,
    after: Any,
    before: Any,
    side: CapitalizerSide,
) -> StructureEvent | None:
    return _find_structure_event(
        bars,
        pivots,
        after=after,
        before=before,
        side=side,
        timeframe=PARENT_STRUCTURE_TIMEFRAME,
    )



@dataclass(frozen=True, slots=True)
class M5CisdEvent:
    confirmed_at: Any
    boundary: Decimal


def _find_m5_cisd(
    bars: tuple[TFBar, ...],
    *,
    after: Any,
    before: Any,
    side: CapitalizerSide,
) -> M5CisdEvent | None:
    boundary: Decimal | None = None
    for bar in bars:
        if not (after < bar.closed_at <= before):
            continue
        source = bar.source
        opposing = (
            source.close < source.open
            if side is CapitalizerSide.LONG
            else source.close > source.open
        )
        if opposing:
            if boundary is None:
                boundary = source.open
            elif side is CapitalizerSide.LONG:
                boundary = max(boundary, source.open)
            else:
                boundary = min(boundary, source.open)
            continue
        if boundary is None:
            continue
        confirmed = (
            source.close > boundary
            if side is CapitalizerSide.LONG
            else source.close < boundary
        )
        if confirmed:
            return M5CisdEvent(confirmed_at=bar.closed_at, boundary=boundary)
    return None




@dataclass(frozen=True, slots=True)
class M3Fvg:
    direction: str
    low: Decimal
    high: Decimal
    formed_at: datetime
    formed_index: int


@dataclass(frozen=True, slots=True)
class H1AnticipationTSpot:
    low: Decimal
    high: Decimal
    defined_at: datetime
    deadline: datetime


@dataclass(frozen=True, slots=True)
class M3EntrySetup:
    entry_index: int
    entry_price: Decimal
    fvg_low: Decimal
    fvg_high: Decimal
    fvg_confirmed_at: datetime
    trigger_at: datetime
    trigger_kind: str
    cisd_boundary: Decimal | None
    entry_mode: str
    order_block_low: Decimal | None
    order_block_high: Decimal | None


def _zone_overlap(
    low_a: Decimal,
    high_a: Decimal,
    low_b: Decimal,
    high_b: Decimal,
) -> tuple[Decimal, Decimal] | None:
    low = max(low_a, low_b)
    high = min(high_a, high_b)
    return None if low > high else (low, high)


def _h1_hour_bounds(moment: datetime) -> tuple[datetime, datetime]:
    local = moment.astimezone(NEW_YORK)
    opened = local.replace(minute=0, second=0, microsecond=0)
    return opened, opened + timedelta(hours=1)


def _h1_anticipation_tspot(
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1: tuple[AggregatedBar, ...],
    *,
    moment: datetime,
    side: CapitalizerSide,
) -> H1AnticipationTSpot | None:
    opened_local, deadline_local = _h1_hour_bounds(moment)
    running = tuple(
        bar
        for bar in all_bars
        if opened_local
        <= bar.opened_at.astimezone(NEW_YORK)
        < deadline_local
        and bar.closed_at <= moment
    )
    if not running:
        return None
    previous = tuple(bar for bar in h1 if bar.closed_at <= opened_local)
    if not previous:
        return None
    prior = previous[-1]
    running_high = max(bar.high for bar in running)
    running_low = min(bar.low for bar in running)
    equilibrium = (running_high + running_low) / Decimal("2")
    extreme = (
        prior.source.low
        if side is CapitalizerSide.LONG
        else prior.source.high
    )
    low = min(equilibrium, extreme)
    high = max(equilibrium, extreme)
    return H1AnticipationTSpot(
        low=low,
        high=high,
        defined_at=moment,
        deadline=deadline_local.astimezone(moment.tzinfo),
    )


def _m3_fvgs(bars: tuple[TFBar, ...]) -> tuple[M3Fvg, ...]:
    result: list[M3Fvg] = []
    for index in range(1, len(bars) - 1):
        first = bars[index - 1]
        third = bars[index + 1]
        if first.source.high < third.source.low:
            result.append(
                M3Fvg(
                    direction="BULLISH",
                    low=first.source.high,
                    high=third.source.low,
                    formed_at=third.closed_at,
                    formed_index=index + 1,
                )
            )
        elif first.source.low > third.source.high:
            result.append(
                M3Fvg(
                    direction="BEARISH",
                    low=third.source.high,
                    high=first.source.low,
                    formed_at=third.closed_at,
                    formed_index=index + 1,
                )
            )
    return tuple(result)


def _latest_opposing_m3_bar(
    bars: tuple[TFBar, ...],
    *,
    before_index: int,
    side: CapitalizerSide,
) -> TFBar | None:
    for index in range(before_index - 1, -1, -1):
        source = bars[index].source
        opposing = (
            source.close < source.open
            if side is CapitalizerSide.LONG
            else source.close > source.open
        )
        if opposing:
            return bars[index]
    return None


def _entry_index_at_or_after(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    moment: datetime,
    before: datetime,
) -> int | None:
    for index, bar in enumerate(execution):
        if bar.opened_at < moment:
            continue
        if bar.opened_at >= before:
            break
        return index
    return None


def _first_m1_touch(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    after: datetime,
    before: datetime,
    price: Decimal,
) -> int | None:
    for index, bar in enumerate(execution):
        if bar.opened_at < after:
            continue
        if bar.opened_at >= before:
            break
        if bar.low <= price <= bar.high:
            return index
    return None


def _find_m3_refinement_entry(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    m3: tuple[TFBar, ...],
    after: datetime,
    deadline: datetime,
    side: CapitalizerSide,
    stop_price: Decimal,
    tspot_low: Decimal,
    tspot_high: Decimal,
    stages: Counter[str],
) -> M3EntrySetup | None:
    eligible = tuple(
        bar for bar in m3 if after < bar.closed_at <= deadline
    )
    if len(eligible) < 1:
        return None

    fvgs = _m3_fvgs(eligible)
    opposing_direction = (
        "BEARISH" if side is CapitalizerSide.LONG else "BULLISH"
    )
    aligned_direction = (
        "BULLISH" if side is CapitalizerSide.LONG else "BEARISH"
    )
    cisd_boundary: Decimal | None = None

    for index, bar in enumerate(eligible):
        source = bar.source
        inside_tspot = (
            source.low <= tspot_high and source.high >= tspot_low
        )
        if not inside_tspot:
            continue

        opposing_bar = (
            source.close < source.open
            if side is CapitalizerSide.LONG
            else source.close > source.open
        )
        if opposing_bar:
            if cisd_boundary is None:
                cisd_boundary = source.open
            elif side is CapitalizerSide.LONG:
                cisd_boundary = max(cisd_boundary, source.open)
            else:
                cisd_boundary = min(cisd_boundary, source.open)

        # Priority 1: inversion FVG. No retest is required.
        opposite_fvgs = tuple(
            fvg
            for fvg in fvgs
            if fvg.direction == opposing_direction
            and fvg.formed_at <= bar.opened_at
        )
        if opposite_fvgs:
            latest = opposite_fvgs[-1]
            inverted = (
                source.close > latest.high
                if side is CapitalizerSide.LONG
                else source.close < latest.low
            )
            if inverted:
                entry_index = _entry_index_at_or_after(
                    execution,
                    moment=bar.closed_at,
                    before=deadline,
                )
                if entry_index is not None:
                    entry_price = source.close
                    valid_stop = (
                        stop_price < entry_price
                        if side is CapitalizerSide.LONG
                        else stop_price > entry_price
                    )
                    if valid_stop:
                        stages["M3_IFVG_TRIGGER"] += 1
                        stages["M3_CLOSE_ENTRY"] += 1
                        return M3EntrySetup(
                            entry_index=entry_index,
                            entry_price=entry_price,
                            fvg_low=latest.low,
                            fvg_high=latest.high,
                            fvg_confirmed_at=latest.formed_at,
                            trigger_at=bar.closed_at,
                            trigger_kind="INVERSION_FVG",
                            cisd_boundary=None,
                            entry_mode="TRIGGER_CLOSE",
                            order_block_low=None,
                            order_block_high=None,
                        )

        # Priority 2: CISD. No FVG/retest requirement.
        if cisd_boundary is not None:
            cisd_confirmed = (
                source.close > cisd_boundary
                if side is CapitalizerSide.LONG
                else source.close < cisd_boundary
            )
            if cisd_confirmed:
                entry_index = _entry_index_at_or_after(
                    execution,
                    moment=bar.closed_at,
                    before=deadline,
                )
                if entry_index is not None:
                    entry_price = source.close
                    valid_stop = (
                        stop_price < entry_price
                        if side is CapitalizerSide.LONG
                        else stop_price > entry_price
                    )
                    if valid_stop:
                        stages["M3_CISD_TRIGGER"] += 1
                        stages["M3_CLOSE_ENTRY"] += 1
                        return M3EntrySetup(
                            entry_index=entry_index,
                            entry_price=entry_price,
                            fvg_low=entry_price,
                            fvg_high=entry_price,
                            fvg_confirmed_at=bar.closed_at,
                            trigger_at=bar.closed_at,
                            trigger_kind="CISD",
                            cisd_boundary=cisd_boundary,
                            entry_mode="TRIGGER_CLOSE",
                            order_block_low=None,
                            order_block_high=None,
                        )

        aligned_fvgs = tuple(
            fvg
            for fvg in fvgs
            if fvg.direction == aligned_direction
            and fvg.formed_at <= bar.closed_at
        )
        if not aligned_fvgs:
            continue
        latest_aligned = aligned_fvgs[-1]

        # Priority 3: OB+FVG confluence. Retest is allowed, not universal.
        ob = _latest_opposing_m3_bar(
            eligible,
            before_index=index,
            side=side,
        )
        if ob is not None:
            overlap = _zone_overlap(
                latest_aligned.low,
                latest_aligned.high,
                ob.source.low,
                ob.source.high,
            )
            if overlap is not None:
                stages["M3_OB_FVG_TRIGGER"] += 1
                retest_price = (
                    overlap[1]
                    if side is CapitalizerSide.LONG
                    else overlap[0]
                )
                entry_index = _first_m1_touch(
                    execution,
                    after=bar.closed_at,
                    before=deadline,
                    price=retest_price,
                )
                if entry_index is not None:
                    valid_stop = (
                        stop_price < retest_price
                        if side is CapitalizerSide.LONG
                        else stop_price > retest_price
                    )
                    if valid_stop:
                        stages["M3_OB_FVG_ENTRY"] += 1
                        return M3EntrySetup(
                            entry_index=entry_index,
                            entry_price=retest_price,
                            fvg_low=latest_aligned.low,
                            fvg_high=latest_aligned.high,
                            fvg_confirmed_at=latest_aligned.formed_at,
                            trigger_at=bar.closed_at,
                            trigger_kind="OB_FVG",
                            cisd_boundary=None,
                            entry_mode="OB_FVG_RETEST",
                            order_block_low=overlap[0],
                            order_block_high=overlap[1],
                        )

        # Priority 4: simple aligned FVG at CE.
        stages["M3_SIMPLE_FVG_TRIGGER"] += 1
        ce = (
            latest_aligned.low + latest_aligned.high
        ) / Decimal("2")
        entry_index = _first_m1_touch(
            execution,
            after=latest_aligned.formed_at,
            before=deadline,
            price=ce,
        )
        if entry_index is not None:
            valid_stop = (
                stop_price < ce
                if side is CapitalizerSide.LONG
                else stop_price > ce
            )
            if valid_stop:
                stages["M3_CE_ENTRY"] += 1
                return M3EntrySetup(
                    entry_index=entry_index,
                    entry_price=ce,
                    fvg_low=latest_aligned.low,
                    fvg_high=latest_aligned.high,
                    fvg_confirmed_at=latest_aligned.formed_at,
                    trigger_at=bar.closed_at,
                    trigger_kind="FVG",
                    cisd_boundary=None,
                    entry_mode="FVG_CE_50",
                    order_block_low=None,
                    order_block_high=None,
                )
    return None



def _lifecycle_2r_or_h1_deadline(
    bars: tuple[CapitalizerM1Bar, ...],
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
        raise ValueError("Capitalizer lifecycle requires positive risk")
    time_exit_at = deadline
    last_close = entry_price
    held = 0
    ambiguity = False

    for index in range(entry_index, len(bars)):
        bar = bars[index]
        if index > entry_index and bar.opened_at >= time_exit_at:
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
        if index == entry_index:
            if stop_hit:
                return Decimal("-1"), "STOP", held, target_hit, bar.closed_at
            continue
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
    return delta / risk, "SESSION_EXIT", held, ambiguity, bars[-1].closed_at



def _metrics(
    trades: tuple[AnticipationTrade, ...],
) -> ICTReplayMetrics | None:
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



def _scan_operating_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    reference: ReferenceLiquidity | None,
    execution: tuple[CapitalizerM1Bar, ...],
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1: tuple[AggregatedBar, ...],
    bias_events: tuple[HTFBiasEvent, ...],
    m5: tuple[TFBar, ...],
    m5_pivots: tuple[Pivot, ...],
    m3: tuple[TFBar, ...],
    stages: Counter[str],
) -> tuple[AnticipationTrade, ...]:
    if reference is None:
        stages["REFERENCE_LIQUIDITY_UNAVAILABLE"] += 1
        return ()
    stages["REFERENCE_LIQUIDITY_AVAILABLE"] += 1

    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return ()

    # Activate the sweep once. It persists as session state.
    sweep_index: int | None = None
    state_bias: HTFBiasEvent | None = None
    state_side: CapitalizerSide | None = None
    saw_h1_bias = False
    for index, bar in enumerate(execution):
        candidate_bias = _immediate_h1_bias(
            h1,
            bias_events,
            bar.opened_at,
        )
        if candidate_bias is None:
            continue
        if not saw_h1_bias:
            stages["SESSION_H1_BIAS_AVAILABLE"] += 1
            saw_h1_bias = True
        stages["H1_GATE_PASS"] += 1
        candidate_side = _side_from_bias(candidate_bias)
        if _sweep_confirmed(
            bar,
            side=candidate_side,
            reference=reference,
        ):
            sweep_index = index
            state_bias = candidate_bias
            state_side = candidate_side
            stages["PRIOR_SESSION_SWEEP"] += 1
            stages["SWEEP_STATE_ACTIVATED"] += 1
            break

    if (
        sweep_index is None
        or state_bias is None
        or state_side is None
    ):
        stages["NO_SESSION_SWEEP_STATE"] += 1
        return ()

    sweep_bar = execution[sweep_index]
    window_end = execution[-1].closed_at
    results: list[AnticipationTrade] = []
    cursor = sweep_index + 1

    while (
        cursor < len(execution)
        and len(results) < MAX_EXECUTIONS_PER_SESSION
    ):
        search_after = max(
            sweep_bar.closed_at,
            execution[cursor].opened_at,
        )

        cisd = _find_m5_cisd(
            m5,
            after=search_after,
            before=window_end,
            side=state_side,
        )
        if cisd is None:
            stages["M5_CISD_MISSING"] += 1
            break
        stages["M5_CISD_PASS"] += 1

        m5_event = _find_m5_parent_structure(
            m5,
            m5_pivots,
            after=search_after,
            before=window_end,
            side=state_side,
        )
        if m5_event is None:
            stages["M5_MSS_MISSING"] += 1
            break
        stages["M5_MSS_PASS"] += 1

        m5_ready_at = max(cisd.confirmed_at, m5_event.confirmed_at)
        tspot = _h1_anticipation_tspot(
            all_bars,
            h1,
            moment=m5_ready_at,
            side=state_side,
        )
        if tspot is None:
            stages["H1_TSPOT_UNAVAILABLE"] += 1
            next_index = next(
                (
                    i
                    for i in range(cursor, len(execution))
                    if execution[i].opened_at >= m5_ready_at
                ),
                len(execution),
            )
            cursor = max(cursor + 1, next_index)
            continue
        stages["H1_TSPOT_DEFINED"] += 1

        trigger_deadline = min(tspot.deadline, window_end)
        if trigger_deadline <= m5_ready_at:
            stages["H1_TRIGGER_WINDOW_EXPIRED"] += 1
            next_index = next(
                (
                    i
                    for i in range(cursor, len(execution))
                    if execution[i].opened_at >= tspot.deadline
                ),
                len(execution),
            )
            cursor = max(cursor + 1, next_index)
            continue

        setup = _find_m3_refinement_entry(
            execution,
            m3=m3,
            after=m5_ready_at,
            deadline=trigger_deadline,
            side=state_side,
            stop_price=m5_event.protected_swing_price,
            tspot_low=tspot.low,
            tspot_high=tspot.high,
            stages=stages,
        )
        if setup is None:
            stages["M3_EXECUTION_MISSING"] += 1
            next_index = next(
                (
                    i
                    for i in range(cursor, len(execution))
                    if execution[i].opened_at >= trigger_deadline
                ),
                len(execution),
            )
            cursor = max(cursor + 1, next_index)
            continue

        entry_index = setup.entry_index
        entry_price = setup.entry_price
        risk = abs(entry_price - m5_event.protected_swing_price)
        if risk <= 0:
            stages["NONPOSITIVE_RISK"] += 1
            cursor = entry_index + 1
            continue

        target = (
            entry_price + Decimal("2") * risk
            if state_side is CapitalizerSide.LONG
            else entry_price - Decimal("2") * risk
        )
        realized, reason, held, ambiguous, exit_at = (
            _lifecycle_2r_or_h1_deadline(
                execution,
                entry_index=entry_index,
                side=state_side,
                entry_price=entry_price,
                stop_price=m5_event.protected_swing_price,
                target_price=target,
                deadline=trigger_deadline,
            )
        )
        stages["ENTRY_EXECUTED"] += 1
        results.append(
            AnticipationTrade(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=state_side.value,
                h1_bias_confirmed_at=state_bias.confirmed_at.isoformat(),
                h1_closure_kind=state_bias.closure_kind,
                h1_poi_kind=state_bias.poi_kind,
                reference_liquidity_source=reference.source,
                reference_high=str(reference.high),
                reference_low=str(reference.low),
                sweep_at=sweep_bar.opened_at.isoformat(),
                sweep_level=str(
                    _sweep_level(side=state_side, reference=reference)
                ),
                sweep_extreme=str(
                    _sweep_extreme(sweep_bar, side=state_side)
                ),
                m5_confirmed_at=m5_event.confirmed_at.isoformat(),
                m5_break_price=str(m5_event.break_price),
                m5_protected_swing_price=str(
                    m5_event.protected_swing_price
                ),
                m5_cisd_confirmed_at=cisd.confirmed_at.isoformat(),
                m5_cisd_boundary=str(cisd.boundary),
                h1_tspot_low=str(tspot.low),
                h1_tspot_high=str(tspot.high),
                h1_tspot_defined_at=tspot.defined_at.isoformat(),
                h1_trigger_deadline=trigger_deadline.isoformat(),
                m3_trigger_at=setup.trigger_at.isoformat(),
                m3_trigger_kind=setup.trigger_kind,
                m3_cisd_boundary=(
                    None
                    if setup.cisd_boundary is None
                    else str(setup.cisd_boundary)
                ),
                m3_fvg_confirmed_at=setup.fvg_confirmed_at.isoformat(),
                m3_fvg_low=str(setup.fvg_low),
                m3_fvg_high=str(setup.fvg_high),
                m3_entry_mode=setup.entry_mode,
                m3_order_block_low=(
                    None
                    if setup.order_block_low is None
                    else str(setup.order_block_low)
                ),
                m3_order_block_high=(
                    None
                    if setup.order_block_high is None
                    else str(setup.order_block_high)
                ),
                m3_entry_reference_price=str(entry_price),
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
) -> tuple[AnticipationMarketReport, tuple[AnticipationTrade, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("owner-h1-m5-m3-anticipation-state replay found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("owner-h1-m5-m3-anticipation-state replay requires one symbol per M1 root")

    h1 = _aggregate_h1(all_bars)
    bias_events = _build_htf_bias_events(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_pivots = _pivots(m5)
    m3 = _aggregate_tf(all_bars, minutes=3)

    execution_by_day, reference_by_day = _index_day_inputs(
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
    trades: list[AnticipationTrade] = []
    per_day: Counter[str] = Counter()

    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        produced = _scan_operating_day(
            symbol=symbol,
            session=session,
            operating_day=operating_day,
            reference=reference_by_day.get(value),
            execution=execution_by_day.get(value, ()),
            all_bars=all_bars,
            h1=h1,
            bias_events=bias_events,
            m5=m5,
            m5_pivots=m5_pivots,
            m3=m3,
            stages=stages,
        )
        trades.extend(produced)
        per_day[value] += len(produced)

    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    report = AnticipationMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        operating_sessions_scanned=len(grouped_dates),
        sessions_with_reference_liquidity=stages[
            "REFERENCE_LIQUIDITY_AVAILABLE"
        ],
        sessions_with_h1_bias=stages["SESSION_H1_BIAS_AVAILABLE"],
        h1_gate_passes=stages["H1_GATE_PASS"],
        prior_session_sweeps=stages["PRIOR_SESSION_SWEEP"],
        sweep_state_activations=stages["SWEEP_STATE_ACTIVATED"],
        m5_structure_passes=stages["M5_MSS_PASS"],
        m5_cisd_passes=stages["M5_CISD_PASS"],
        m5_mss_passes=stages["M5_MSS_PASS"],
        h1_tspot_definitions=stages["H1_TSPOT_DEFINED"],
        m3_ifvg_triggers=stages["M3_IFVG_TRIGGER"],
        m3_cisd_triggers=stages["M3_CISD_TRIGGER"],
        m3_ob_fvg_triggers=stages["M3_OB_FVG_TRIGGER"],
        m3_simple_fvg_triggers=stages["M3_SIMPLE_FVG_TRIGGER"],
        m3_ob_fvg_entries=stages["M3_OB_FVG_ENTRY"],
        m3_ce_entries=stages["M3_CE_ENTRY"],
        m3_close_entries=stages["M3_CLOSE_ENTRY"],
        raw_entries=len(ordered),
        raw_metrics=_metrics(ordered),
        raw_stop_exits=sum(
            item.exit_reason == "STOP" for item in ordered
        ),
        raw_target_exits=sum(
            item.exit_reason == "TARGET" for item in ordered
        ),
        raw_session_exits=sum(
            item.exit_reason == "SESSION_EXIT" for item in ordered
        ),
        raw_time_exits=sum(
            item.exit_reason == "TIME_EXIT" for item in ordered
        ),
        sessions_with_entry=sum(count > 0 for count in per_day.values()),
        max_entries_one_market_session=max(per_day.values(), default=0),
        stage_counts=tuple(
            sorted(stages.items(), key=lambda item: (-item[1], item[0]))
        ),
    )
    return report, ordered


def write_market(
    report: AnticipationMarketReport,
    trades: tuple[AnticipationTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = (
        f"capitalizer-{report.symbol.lower()}-owner-h1-m5-m3-anticipation-state-1y-v2"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-owner-h1-m5-m3-anticipation-state-1y-v2.json")
    )
    if len(paths) != 9:
        raise ValueError(
            f"owner-h1-m5-m3-anticipation-state matrix requires 9 reports, got {len(paths)}"
        )
    reports: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("identity") != IDENTITY:
            raise ValueError("unexpected owner-h1-m5-m3-anticipation-state market report")
        reports.append(dict(raw))
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("owner-h1-m5-m3-anticipation-state universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def _load_trades(root: Path) -> tuple[AnticipationTrade, ...]:
    rows: list[AnticipationTrade] = []
    pattern = "capitalizer-*-owner-h1-m5-m3-anticipation-state-1y-v2-trades.jsonl"
    for path in sorted(root.rglob(pattern)):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(AnticipationTrade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _portfolio_max3(
    trades: tuple[AnticipationTrade, ...],
) -> tuple[AnticipationTrade, ...]:
    grouped: dict[str, list[AnticipationTrade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)

    selected: list[AnticipationTrade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _monthly_counts(
    trades: tuple[AnticipationTrade, ...],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for trade in trades:
        counts[trade.operating_date[:7]] += 1
    return dict(sorted(counts.items()))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = _portfolio_max3(raw)

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        session_raw = tuple(
            item for item in raw if item.session == session.value
        )
        session_max3 = tuple(
            item for item in max3 if item.session == session.value
        )
        per_session[session.value] = {
            "raw_trades": len(session_raw),
            "raw_metrics": (
                None
                if (value := _metrics(session_raw)) is None
                else asdict(value)
            ),
            "max3_trades": len(session_max3),
            "max3_metrics": (
                None
                if (value := _metrics(session_max3)) is None
                else asdict(value)
            ),
        }

    raw_metrics = _metrics(raw)
    max3_metrics = _metrics(max3)
    distinct_days = len({item.operating_date for item in max3})
    calendar_days = (WINDOW_END.date() - WINDOW_START.date()).days

    return {
        "identity": MATRIX_IDENTITY,
        "architecture": (
            "H1_BIAS_TO_SWEEP_SESSION_STATE_TO_M5_CISD_MSS_TO_"
            "H1_ANTICIPATION_TSPOT_TO_M3"
        ),
        "architecture_predeclared": True,
        "parent_structure_timeframe": PARENT_STRUCTURE_TIMEFRAME,
        "m15_gate_required": False,
        "entry_identity": ENTRY_IDENTITY,
        "stop_identity": STOP_IDENTITY,
        "target_identity": TARGET_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "raw_trades": len(raw),
        "raw_metrics": None if raw_metrics is None else asdict(raw_metrics),
        "raw_stop_exits": sum(
            item.exit_reason == "STOP" for item in raw
        ),
        "raw_target_exits": sum(
            item.exit_reason == "TARGET" for item in raw
        ),
        "raw_session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in raw
        ),
        "raw_time_exits": sum(
            item.exit_reason == "TIME_EXIT" for item in raw
        ),
        "max3_selected_trades": len(max3),
        "max3_metrics": (
            None if max3_metrics is None else asdict(max3_metrics)
        ),
        "max3_stop_exits": sum(
            item.exit_reason == "STOP" for item in max3
        ),
        "max3_target_exits": sum(
            item.exit_reason == "TARGET" for item in max3
        ),
        "max3_session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in max3
        ),
        "max3_time_exits": sum(
            item.exit_reason == "TIME_EXIT" for item in max3
        ),
        "sessions_with_h1_bias": sum(
            int(item["sessions_with_h1_bias"]) for item in reports
        ),
        "h1_gate_passes": sum(
            int(item["h1_gate_passes"]) for item in reports
        ),
        "prior_session_sweeps": sum(
            int(item["prior_session_sweeps"]) for item in reports
        ),
        "sweep_state_activations": sum(
            int(item["sweep_state_activations"]) for item in reports
        ),
        "m5_structure_passes": sum(
            int(item["m5_structure_passes"]) for item in reports
        ),
        "m5_cisd_passes": sum(
            int(item["m5_cisd_passes"]) for item in reports
        ),
        "m5_mss_passes": sum(
            int(item["m5_mss_passes"]) for item in reports
        ),
        "h1_tspot_definitions": sum(
            int(item["h1_tspot_definitions"]) for item in reports
        ),
        "m3_ifvg_triggers": sum(
            int(item["m3_ifvg_triggers"]) for item in reports
        ),
        "m3_cisd_triggers": sum(
            int(item["m3_cisd_triggers"]) for item in reports
        ),
        "m3_ob_fvg_triggers": sum(
            int(item["m3_ob_fvg_triggers"]) for item in reports
        ),
        "m3_simple_fvg_triggers": sum(
            int(item["m3_simple_fvg_triggers"]) for item in reports
        ),
        "m3_ob_fvg_entries": sum(
            int(item["m3_ob_fvg_entries"]) for item in reports
        ),
        "m3_ce_entries": sum(
            int(item["m3_ce_entries"]) for item in reports
        ),
        "m3_close_entries": sum(
            int(item["m3_close_entries"]) for item in reports
        ),
        "monthly_max3_trades": _monthly_counts(max3),
        "days_with_any_trade": distinct_days,
        "calendar_days": calendar_days,
        "max3_trades_per_calendar_day": (
            0.0 if calendar_days == 0 else len(max3) / calendar_days
        ),
        "annualized_max3_trades": len(max3),
        "per_session": per_session,
        "markets": reports,
        "max3_is_ceiling_not_quota": True,
        "methodology_research_only": True,
        "daily_driver_used": False,
        "entry_timeframe": "M3",
        "m3_mss_required": False,
        "sweep_state_persistent": True,
        "tspot_definition": "RUNNING_H1_EQ_TO_PREVIOUS_H1_EXTREME",
        "trigger_deadline_definition": "SAME_H1_CLOSE",
        "m3_trigger_logic": "IFVG_THEN_CISD_THEN_OBFVG_THEN_FVG",
        "entry_mode_logic": "TRIGGER_CLOSE_OR_FVG_CE_OR_OBFVG_RETEST",
        "time_exit": "SAME_H1_CLOSE",
        "m5_cisd_required": True,
        "m5_mss_required": True,
        "m1_intrabar_only": True,
        "m1_can_originate_trade": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-owner-h1-m5-m3-anticipation-state-1y-matrix-v1.json"
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
                    "trades": report.raw_entries,
                    "pf": (
                        None
                        if report.raw_metrics is None
                        else report.raw_metrics.profit_factor
                    ),
                    "stops": report.raw_stop_exits,
                    "targets": report.raw_target_exits,
                    "session_exits": report.raw_session_exits,
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
