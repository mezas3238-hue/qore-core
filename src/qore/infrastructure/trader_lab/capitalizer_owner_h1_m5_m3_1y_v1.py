"""Owner-frozen QORE Capitalizer H1-M5-M3 1Y replay.

Exact Owner strategy:
    H1 bias
    -> liquidity sweep
    -> M5 CISD + MSS
    -> M5 T-Spot
    -> M3 refinement
    -> M3 inversion FVG OR M3 CISD inside the T-Spot
    -> OB+FVG confluence when present
    -> entry at FVG CE 50% OR OB+FVG retest
    -> M3 entry

Risk/lifecycle:
    stop = M5 protected swing
    target = fixed 2R OR next H1-open time exit
    same-session hard lifecycle
    same-minute stop/target ambiguity = STOP_FIRST
    MAX3/session = ceiling, never quota

M1 is retained only for exact intrabar fill/stop/target/time-exit precedence.
M1 cannot originate or authorize a trade.

No M15 gate. No mandatory M3 MSS. No source-specific strategy substitution.
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

IDENTITY = "QORE_CAPITALIZER_OWNER_H1_M5_M3_1Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_OWNER_H1_M5_M3_1Y_MATRIX_V1"
)
ENTRY_IDENTITY = "H1_BIAS__LIQUIDITY_SWEEP__M5_CISD_MSS_TSPOT__M3_IFVG_OR_CISD__CE_OR_OBFVG_RETEST"
STOP_IDENTITY = "M5_PROTECTED_SWING"
TARGET_IDENTITY = "FIXED_2R_OR_NEXT_H1_OPEN"
PARENT_STRUCTURE_TIMEFRAME = "M5"
LOOKBACK_START = WINDOW_START - timedelta(days=14)
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
class OwnerM3Trade:
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
    m5_tspot_low: str
    m5_tspot_high: str
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
    parent_structure_timeframe: str = PARENT_STRUCTURE_TIMEFRAME
    m15_gate_required: bool = False
    entry_timeframe: str = "M3"
    m5_cisd_required: bool = True
    m5_mss_required: bool = True
    m3_mss_required: bool = False
    m3_trigger_logic: str = "INVERSION_FVG_OR_CISD"
    entry_mode_logic: str = "FVG_CE_50_OR_OB_FVG_RETEST"
    time_exit: str = "NEXT_H1_OPEN"
    m1_intrabar_only: bool = True
    m1_originated_trade: bool = False
    daily_driver_used: bool = False
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class OwnerM3MarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    operating_sessions_scanned: int
    sessions_with_reference_liquidity: int
    h1_gate_passes: int
    prior_session_sweeps: int
    m5_structure_passes: int
    m5_cisd_passes: int
    m5_mss_passes: int
    m3_ifvg_triggers: int
    m3_cisd_triggers: int
    m3_fvg_entry_zones: int
    m3_ob_fvg_entries: int
    m3_ce_entries: int
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
    daily_driver_used: bool = False
    entry_timeframe: str = "M3"
    m5_cisd_required: bool = True
    m5_mss_required: bool = True
    m3_mss_required: bool = False
    m3_trigger_logic: str = "INVERSION_FVG_OR_CISD"
    entry_mode_logic: str = "FVG_CE_50_OR_OB_FVG_RETEST"
    time_exit: str = "NEXT_H1_OPEN"
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


def _m5_tspot(
    *,
    cisd: M5CisdEvent,
    mss: StructureEvent,
) -> tuple[Decimal, Decimal]:
    low = min(cisd.boundary, mss.protected_swing_price)
    high = max(cisd.boundary, mss.protected_swing_price)
    return low, high


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
    before: datetime,
    side: CapitalizerSide,
    stop_price: Decimal,
    tspot_low: Decimal,
    tspot_high: Decimal,
    stages: Counter[str],
) -> M3EntrySetup | None:
    eligible = tuple(
        bar for bar in m3 if after < bar.closed_at <= before
    )
    if len(eligible) < 3:
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

        trigger_kind: str | None = None
        trigger_fvg: M3Fvg | None = None
        trigger_cisd_boundary: Decimal | None = None

        opposite_fvgs = tuple(
            fvg
            for fvg in fvgs
            if fvg.direction == opposing_direction
            and fvg.formed_at <= bar.opened_at
            and _zone_overlap(
                fvg.low, fvg.high, tspot_low, tspot_high
            )
            is not None
        )
        if opposite_fvgs:
            latest = opposite_fvgs[-1]
            inverted = (
                source.close > latest.high
                if side is CapitalizerSide.LONG
                else source.close < latest.low
            )
            if inverted:
                trigger_kind = "INVERSION_FVG"
                trigger_fvg = latest
                stages["M3_IFVG_TRIGGER"] += 1

        if trigger_kind is None and cisd_boundary is not None:
            cisd_confirmed = (
                source.close > cisd_boundary
                if side is CapitalizerSide.LONG
                else source.close < cisd_boundary
            )
            if cisd_confirmed:
                trigger_kind = "CISD"
                trigger_cisd_boundary = cisd_boundary
                stages["M3_CISD_TRIGGER"] += 1

        if trigger_kind is None:
            continue

        if not (
            source.low <= tspot_high and source.high >= tspot_low
        ):
            stages["M3_TRIGGER_OUTSIDE_TSPOT"] += 1
            continue

        if trigger_fvg is None:
            aligned_fvgs = tuple(
                fvg
                for fvg in fvgs
                if fvg.direction == aligned_direction
                and fvg.formed_at >= bar.closed_at
                and fvg.formed_at <= before
                and _zone_overlap(
                    fvg.low, fvg.high, tspot_low, tspot_high
                )
                is not None
            )
            if not aligned_fvgs:
                stages["M3_CISD_WITHOUT_ENTRY_FVG"] += 1
                continue
            trigger_fvg = aligned_fvgs[0]

        stages["M3_FVG_ENTRY_ZONE"] += 1
        fvg_low, fvg_high = trigger_fvg.low, trigger_fvg.high
        ob = _latest_opposing_m3_bar(
            eligible,
            before_index=index,
            side=side,
        )
        ob_low: Decimal | None = None
        ob_high: Decimal | None = None
        entry_mode = "FVG_CE_50"
        entry_price = (fvg_low + fvg_high) / Decimal("2")

        if ob is not None:
            overlap = _zone_overlap(
                fvg_low,
                fvg_high,
                ob.source.low,
                ob.source.high,
            )
            if overlap is not None:
                ob_low, ob_high = overlap
                entry_mode = "OB_FVG_RETEST"
                entry_price = (
                    overlap[1]
                    if side is CapitalizerSide.LONG
                    else overlap[0]
                )

        valid_stop = (
            stop_price < entry_price
            if side is CapitalizerSide.LONG
            else stop_price > entry_price
        )
        if not valid_stop:
            stages["M5_PROTECTED_SWING_INVALID_GEOMETRY"] += 1
            continue

        touch_after = max(bar.closed_at, trigger_fvg.formed_at)
        entry_index = _first_m1_touch(
            execution,
            after=touch_after,
            before=before,
            price=entry_price,
        )
        if entry_index is None:
            stages["M3_ENTRY_RETEST_MISSING"] += 1
            continue

        if entry_mode == "OB_FVG_RETEST":
            stages["M3_OB_FVG_ENTRY"] += 1
        else:
            return M3EntrySetup(
            entry_index=entry_index,
            entry_price=entry_price,
            fvg_low=fvg_low,
            fvg_high=fvg_high,
            fvg_confirmed_at=trigger_fvg.formed_at,
            trigger_at=bar.closed_at,
            trigger_kind=trigger_kind,
            cisd_boundary=trigger_cisd_boundary,
            entry_mode=entry_mode,
            order_block_low=ob_low,
            order_block_high=ob_high,
        )
    return None


def _lifecycle_2r_or_next_h1(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    entry_index: int,
    side: CapitalizerSide,
    entry_price: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
) -> tuple[Decimal, str, int, bool, datetime]:
    risk = abs(entry_price - stop_price)
    if risk <= 0:
        raise ValueError("Capitalizer lifecycle requires positive risk")
    entry_at = bars[entry_index].opened_at
    time_exit_at = entry_at.replace(
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(hours=1)
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
    trades: tuple[OwnerM3Trade, ...],
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
    h1: tuple[AggregatedBar, ...],
    bias_events: tuple[HTFBiasEvent, ...],
    m5: tuple[TFBar, ...],
    m5_pivots: tuple[Pivot, ...],
    m3: tuple[TFBar, ...],
    stages: Counter[str],
) -> tuple[OwnerM3Trade, ...]:
    if reference is None:
        stages["REFERENCE_LIQUIDITY_UNAVAILABLE"] += 1
        return ()
    stages["REFERENCE_LIQUIDITY_AVAILABLE"] += 1

    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return ()
    results: list[OwnerM3Trade] = []
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

        cisd = _find_m5_cisd(
            m5,
            after=sweep_bar.closed_at,
            before=window_end,
            side=side,
        )
        if cisd is None:
            stages["M5_CISD_MISSING"] += 1
            cursor = sweep_index + 1
            continue
        stages["M5_CISD_PASS"] += 1

        m5_event = _find_m5_parent_structure(
            m5,
            m5_pivots,
            after=sweep_bar.closed_at,
            before=window_end,
            side=side,
        )
        if m5_event is None:
            stages["M5_MSS_MISSING"] += 1
            cursor = sweep_index + 1
            continue
        stages["M5_MSS_PASS"] += 1

        m5_ready_at = max(cisd.confirmed_at, m5_event.confirmed_at)
        tspot_low, tspot_high = _m5_tspot(
            cisd=cisd,
            mss=m5_event,
        )
        stages["M5_TSPOT_DEFINED"] += 1

        setup = _find_m3_refinement_entry(
            execution,
            m3=m3,
            after=m5_ready_at,
            before=window_end,
            side=side,
            stop_price=m5_event.protected_swing_price,
            tspot_low=tspot_low,
            tspot_high=tspot_high,
            stages=stages,
        )
        if setup is None:
            stages["M3_EXECUTION_MISSING"] += 1
            cursor = sweep_index + 1
            continue

        entry_index = setup.entry_index
        entry_price = setup.entry_price
        fvg_low = setup.fvg_low
        fvg_high = setup.fvg_high
        fvg_confirmed_at = setup.fvg_confirmed_at

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
        realized, reason, held, ambiguous, exit_at = _lifecycle_2r_or_next_h1(
            execution,
            entry_index=entry_index,
            side=side,
            entry_price=entry_price,
            stop_price=m5_event.protected_swing_price,
            target_price=target,
        )
        stages["M3_CE_ENTRY"] += 1
        results.append(
            OwnerM3Trade(
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
                sweep_level=str(
                    _sweep_level(side=side, reference=reference)
                ),
                sweep_extreme=str(_sweep_extreme(sweep_bar, side=side)),
                m5_confirmed_at=m5_event.confirmed_at.isoformat(),
                m5_break_price=str(m5_event.break_price),
                m5_protected_swing_price=str(
                    m5_event.protected_swing_price
                ),
                m5_cisd_confirmed_at=cisd.confirmed_at.isoformat(),
                m5_cisd_boundary=str(cisd.boundary),
                m5_tspot_low=str(tspot_low),
                m5_tspot_high=str(tspot_high),
                m3_trigger_at=setup.trigger_at.isoformat(),
                m3_trigger_kind=setup.trigger_kind,
                m3_cisd_boundary=(
                    None
                    if setup.cisd_boundary is None
                    else str(setup.cisd_boundary)
                ),
                m3_fvg_confirmed_at=fvg_confirmed_at.isoformat(),
                m3_fvg_low=str(fvg_low),
                m3_fvg_high=str(fvg_high),
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
) -> tuple[OwnerM3MarketReport, tuple[OwnerM3Trade, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("owner-h1-m5-m3 replay found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("owner-h1-m5-m3 replay requires one symbol per M1 root")

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
    trades: list[OwnerM3Trade] = []
    per_day: Counter[str] = Counter()

    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        produced = _scan_operating_day(
            symbol=symbol,
            session=session,
            operating_day=operating_day,
            reference=reference_by_day.get(value),
            execution=execution_by_day.get(value, ()),
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
    report = OwnerM3MarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        operating_sessions_scanned=len(grouped_dates),
        sessions_with_reference_liquidity=stages[
            "REFERENCE_LIQUIDITY_AVAILABLE"
        ],
        h1_gate_passes=stages["H1_GATE_PASS"],
        prior_session_sweeps=stages["PRIOR_SESSION_SWEEP"],
        m5_structure_passes=stages["M5_MSS_PASS"],
        m5_cisd_passes=stages["M5_CISD_PASS"],
        m5_mss_passes=stages["M5_MSS_PASS"],
        m3_ifvg_triggers=stages["M3_IFVG_TRIGGER"],
        m3_cisd_triggers=stages["M3_CISD_TRIGGER"],
        m3_fvg_entry_zones=stages["M3_FVG_ENTRY_ZONE"],
        m3_ob_fvg_entries=stages["M3_OB_FVG_ENTRY"],
        m3_ce_entries=stages["M3_CE_ENTRY"],
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
    report: OwnerM3MarketReport,
    trades: tuple[OwnerM3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = (
        f"capitalizer-{report.symbol.lower()}-owner-h1-m5-m3-1y-v1"
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
        root.rglob("capitalizer-*-owner-h1-m5-m3-1y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(
            f"owner-h1-m5-m3 matrix requires 9 reports, got {len(paths)}"
        )
    reports: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("identity") != IDENTITY:
            raise ValueError("unexpected owner-h1-m5-m3 market report")
        reports.append(dict(raw))
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("owner-h1-m5-m3 universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def _load_trades(root: Path) -> tuple[OwnerM3Trade, ...]:
    rows: list[OwnerM3Trade] = []
    pattern = "capitalizer-*-owner-h1-m5-m3-1y-v1-trades.jsonl"
    for path in sorted(root.rglob(pattern)):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(OwnerM3Trade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _portfolio_max3(
    trades: tuple[OwnerM3Trade, ...],
) -> tuple[OwnerM3Trade, ...]:
    grouped: dict[str, list[OwnerM3Trade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)

    selected: list[OwnerM3Trade] = []
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
    trades: tuple[OwnerM3Trade, ...],
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
        "architecture": "H1_BIAS_TO_LIQUIDITY_SWEEP_TO_M5_CISD_MSS_TSPOT_TO_M3",
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
        "h1_gate_passes": sum(
            int(item["h1_gate_passes"]) for item in reports
        ),
        "prior_session_sweeps": sum(
            int(item["prior_session_sweeps"]) for item in reports
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
        "m3_ifvg_triggers": sum(
            int(item["m3_ifvg_triggers"]) for item in reports
        ),
        "m3_cisd_triggers": sum(
            int(item["m3_cisd_triggers"]) for item in reports
        ),
        "m3_fvg_entry_zones": sum(
            int(item["m3_fvg_entry_zones"]) for item in reports
        ),
        "m3_ob_fvg_entries": sum(
            int(item["m3_ob_fvg_entries"]) for item in reports
        ),
        "m3_ce_entries": sum(
            int(item["m3_ce_entries"]) for item in reports
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
        "m3_trigger_logic": "INVERSION_FVG_OR_CISD",
        "entry_mode_logic": "FVG_CE_50_OR_OB_FVG_RETEST",
        "time_exit": "NEXT_H1_OPEN",
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
        "capitalizer-nine-market-owner-h1-m5-m3-1y-matrix-v1.json"
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
