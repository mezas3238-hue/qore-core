"""Full-density Capitalizer scanner using the ICT M1 execution chain over native M1.

Research objective
------------------
Measure the density and raw economics of the trader when the old higher-level
candidate ledger is removed from the admission path.

Frozen chain:
    HTF bias/context
    -> structural liquidity objective
    -> M1 liquidity raid
    -> directional displacement
    -> M1 market-structure shift
    -> directional M1 fair value gap
    -> first causal retracement into that FVG
    -> entry

Important provenance boundary
-----------------------------
HTF context is the already-frozen Capitalizer mechanical source route:
the latest causal H1 Candle-2/Candle-3 closure at a causal H1 POI establishes
direction. This is Capitalizer/TTrades mechanical context, not relabeled as an
ICT-original daily-bias formula.

The structural objective is the most recent completed New-York trading day's
high for bullish context or low for bearish context, consistent with the
reviewed structural-liquidity objective family.

Execution uses the ICT 2022 M1 chain. It does NOT require an Order Block.

Replay controls
---------------
Window: [2025-09-17, 2026-09-17)
Universe/session assignment is the frozen Capitalizer contract.
Session buckets are the broad QORE research sessions, not ICT killzones.
Initial stop is the raid extreme (structural invalidation proxy).
Target is the frozen structural liquidity objective.
Lifecycle is same-session and same-minute ambiguity is STOP_FIRST.
Raw density and the frozen portfolio MAX3/session density are both reported.

This module is research only. It does not authorize promotion, live trading,
risk sizing, or real capital.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
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
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    WINDOW_END,
    WINDOW_START,
    ICTReplayMetrics,
    _aware,
    _lifecycle,
    _operating_date,
    _significant_displacement,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    detect_candle2_reversal_closure,
    detect_candle3_confirmation,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    CapitalizerSourcePOIKind,
    bar_interacts_with_poi,
    detect_external_liquidity_swing,
    detect_fair_value_gap,
)

IDENTITY = "QORE_CAPITALIZER_FULL_ICT_DENSITY_SCANNER_1Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_FULL_ICT_DENSITY_1Y_MATRIX_V1"
ENTRY_IDENTITY = "ICT_2022_RAID_DISPLACEMENT_MSS_FVG_FIRST_RETRACE"
HTF_CONTEXT_IDENTITY = "CAPITALIZER_H1_C2_C3_CLOSURE_AT_CAUSAL_POI"
OBJECTIVE_IDENTITY = "MOST_RECENT_COMPLETED_NY_DAY_HIGH_LOW"
STOP_IDENTITY = "M1_RAID_EXTREME_STRUCTURAL_INVALIDATION_PROXY"
TARGET_IDENTITY = "STRUCTURAL_LIQUIDITY_OBJECTIVE"
LOOKBACK_START = WINDOW_START - timedelta(days=10)
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
class AggregatedBar:
    opened_at: datetime
    closed_at: datetime
    source: CapitalizerSourceBar
    minute_count: int


@dataclass(frozen=True, slots=True)
class HTFBiasEvent:
    confirmed_at: datetime
    direction: CapitalizerSourceDirection
    closure_kind: str
    poi_kind: str


@dataclass(frozen=True, slots=True)
class DailyObjective:
    ny_date: str
    high: Decimal
    low: Decimal


@dataclass(frozen=True, slots=True)
class ICTScannerSetup:
    raid_index: int
    raid_extreme: Decimal
    swept_pivot_price: Decimal
    swept_pivot_index: int
    displacement_index: int
    fvg_confirm_index: int
    mss_level: Decimal
    fvg_low: Decimal
    fvg_high: Decimal


@dataclass(frozen=True, slots=True)
class ICTScannerTrade:
    symbol: str
    session: str
    operating_date: str
    side: str
    htf_bias_confirmed_at: str
    htf_bias_age_minutes: int
    htf_closure_kind: str
    htf_poi_kind: str
    objective_source_date: str
    objective_price: str
    raid_at: str
    swept_pivot_price: str
    raid_extreme: str
    displacement_at: str
    mss_level: str
    fvg_confirmed_at: str
    fvg_low: str
    fvg_high: str
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
    htf_context_definition: str = HTF_CONTEXT_IDENTITY
    objective_definition: str = OBJECTIVE_IDENTITY
    stop_definition: str = STOP_IDENTITY
    target_definition: str = TARGET_IDENTITY
    order_block_required: bool = False
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class ICTScannerMarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    operating_sessions_scanned: int
    sessions_with_htf_bias: int
    sessions_without_htf_bias: int
    sessions_with_objective: int
    sessions_objective_wrong_side_at_open: int
    m1_raid_events: int
    m1_displacement_events_after_raid: int
    m1_mss_events_after_raid: int
    m1_fvg_events_after_mss: int
    m1_retrace_entries_raw: int
    raw_metrics: ICTReplayMetrics | None
    raw_stop_exits: int
    raw_target_exits: int
    raw_session_exits: int
    sessions_with_raw_entry: int
    sessions_over_max3_market_raw: int
    max_raw_entries_one_market_session: int
    stage_rejections: tuple[tuple[str, int], ...]
    old_candidate_ledger_used: bool = False
    old_raid_rejection_gate_used: bool = False
    htf_context_changed_from_frozen_capitalizer_route: bool = False
    order_block_required: bool = False
    synthetic_m1_used: bool = False
    interpolated_m1_used: bool = False
    qore_session_bucket_is_ict_killzone: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _aggregate_h1(bars: tuple[CapitalizerM1Bar, ...]) -> tuple[AggregatedBar, ...]:
    grouped: dict[
        tuple[int, int, int, int, int],
        list[CapitalizerM1Bar],
    ] = defaultdict(list)
    for bar in bars:
        local = bar.opened_at.astimezone(NEW_YORK)
        offset = local.utcoffset()
        if offset is None:
            raise ValueError("NY-local M1 bar requires UTC offset")
        grouped[
            (
                local.year,
                local.month,
                local.day,
                local.hour,
                int(offset.total_seconds()),
            )
        ].append(bar)

    result: list[AggregatedBar] = []
    for key in sorted(grouped):
        chunk = sorted(grouped[key], key=lambda item: item.opened_at)
        if len(chunk) < 45:
            continue
        result.append(
            AggregatedBar(
                opened_at=chunk[0].opened_at,
                closed_at=chunk[-1].closed_at,
                source=CapitalizerSourceBar(
                    open=chunk[0].open,
                    high=max(item.high for item in chunk),
                    low=min(item.low for item in chunk),
                    close=chunk[-1].close,
                ),
                minute_count=len(chunk),
            )
        )
    return tuple(result)


def _daily_objectives(
    bars: tuple[CapitalizerM1Bar, ...],
) -> tuple[DailyObjective, ...]:
    grouped: dict[str, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        local = bar.opened_at.astimezone(NEW_YORK)
        grouped[local.date().isoformat()].append(bar)
    result = [
        DailyObjective(
            ny_date=day,
            high=max(item.high for item in chunk),
            low=min(item.low for item in chunk),
        )
        for day, chunk in grouped.items()
        if len(chunk) >= 60
    ]
    return tuple(sorted(result, key=lambda item: item.ny_date))


def _poi_direction_compatible(
    poi: CapitalizerSourcePOI,
    direction: CapitalizerSourceDirection,
) -> bool:
    if direction is CapitalizerSourceDirection.BULLISH:
        return poi.kind in {
            CapitalizerSourcePOIKind.BULLISH_FVG,
            CapitalizerSourcePOIKind.SWING_LOW,
        }
    return poi.kind in {
        CapitalizerSourcePOIKind.BEARISH_FVG,
        CapitalizerSourcePOIKind.SWING_HIGH,
    }


def _build_htf_bias_events(
    h1: tuple[AggregatedBar, ...],
) -> tuple[HTFBiasEvent, ...]:
    if len(h1) < 4:
        return ()

    pois_by_confirm_index: dict[int, list[CapitalizerSourcePOI]] = defaultdict(list)
    for center in range(1, len(h1) - 1):
        triple = (
            h1[center - 1].source,
            h1[center].source,
            h1[center + 1].source,
        )
        fvg = detect_fair_value_gap(
            candle1=triple[0],
            candle2=triple[1],
            candle3=triple[2],
        )
        if fvg is not None:
            pois_by_confirm_index[center + 1].append(fvg)
        swing = detect_external_liquidity_swing(
            left=triple[0],
            center=triple[1],
            right=triple[2],
        )
        if swing is not None:
            pois_by_confirm_index[center + 1].append(swing)

    active_pois: list[tuple[int, CapitalizerSourcePOI]] = []
    events: list[HTFBiasEvent] = []
    previous_interacted: tuple[CapitalizerSourcePOI, ...] = ()
    previous_c2_confirmed = False

    for index in range(1, len(h1)):
        for poi in pois_by_confirm_index.get(index - 1, ()):
            active_pois.append((index - 1, poi))

        current = h1[index].source
        previous = h1[index - 1].source

        # Candle-3 at index uses only the state that belonged to Candle-2
        # at index-1. This prevents the current H1 bar from creating its
        # own prerequisite POI context.
        if index >= 2:
            c3 = detect_candle3_confirmation(
                candle2=previous,
                candle3=current,
                point_of_interest_present=bool(previous_interacted),
                candle2_reversal_already_confirmed=previous_c2_confirmed,
            )
            if c3 is not None and c3.source_rule_satisfied:
                compatible_c3 = tuple(
                    poi
                    for poi in previous_interacted
                    if _poi_direction_compatible(poi, c3.direction)
                )
                if compatible_c3:
                    events.append(
                        HTFBiasEvent(
                            confirmed_at=h1[index].closed_at,
                            direction=c3.direction,
                            closure_kind=c3.kind.value,
                            poi_kind=compatible_c3[0].kind.value,
                        )
                    )

        interacted_bullish = tuple(
            poi
            for _, poi in active_pois
            if _poi_direction_compatible(poi, CapitalizerSourceDirection.BULLISH)
            and bar_interacts_with_poi(bar=current, poi=poi)
        )
        interacted_bearish = tuple(
            poi
            for _, poi in active_pois
            if _poi_direction_compatible(poi, CapitalizerSourceDirection.BEARISH)
            and bar_interacts_with_poi(bar=current, poi=poi)
        )
        interacted = interacted_bullish + interacted_bearish

        c2 = detect_candle2_reversal_closure(
            previous=previous,
            candle2=current,
            point_of_interest_present=bool(interacted),
        )
        current_c2_confirmed = False
        if c2 is not None and c2.source_rule_satisfied:
            compatible_c2 = (
                interacted_bullish
                if c2.direction is CapitalizerSourceDirection.BULLISH
                else interacted_bearish
            )
            current_c2_confirmed = bool(compatible_c2)
            if compatible_c2:
                events.append(
                    HTFBiasEvent(
                        confirmed_at=h1[index].closed_at,
                        direction=c2.direction,
                        closure_kind=c2.kind.value,
                        poi_kind=compatible_c2[0].kind.value,
                    )
                )

        previous_interacted = interacted
        previous_c2_confirmed = current_c2_confirmed

    return tuple(sorted(events, key=lambda item: item.confirmed_at))

def _latest_bias_before(
    events: tuple[HTFBiasEvent, ...],
    event_times: tuple[datetime, ...],
    moment: datetime,
) -> HTFBiasEvent | None:
    index = bisect.bisect_left(event_times, moment) - 1
    return None if index < 0 else events[index]


def _latest_completed_objective(
    objectives: tuple[DailyObjective, ...],
    objective_days: tuple[str, ...],
    session_start: datetime,
) -> DailyObjective | None:
    local_day = session_start.astimezone(NEW_YORK).date().isoformat()
    index = bisect.bisect_left(objective_days, local_day) - 1
    return None if index < 0 else objectives[index]


def _confirmed_pivots(
    bars: tuple[CapitalizerM1Bar, ...],
) -> tuple[
    tuple[tuple[int, Decimal], ...],
    tuple[tuple[int, Decimal], ...],
]:
    highs: list[tuple[int, Decimal]] = []
    lows: list[tuple[int, Decimal]] = []
    for center in range(1, len(bars) - 1):
        left, mid, right = bars[center - 1], bars[center], bars[center + 1]
        if mid.high > left.high and mid.high > right.high:
            highs.append((center, mid.high))
        if mid.low < left.low and mid.low < right.low:
            lows.append((center, mid.low))
    return tuple(highs), tuple(lows)


def _latest_pivot(
    pivots: tuple[tuple[int, Decimal], ...],
    *,
    before_index: int,
) -> tuple[int, Decimal] | None:
    positions = [item[0] for item in pivots]
    index = bisect.bisect_left(positions, before_index) - 1
    return None if index < 0 else pivots[index]


def _objective_touched(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    objective: Decimal,
) -> bool:
    return (
        bar.high >= objective
        if side is CapitalizerSide.LONG
        else bar.low <= objective
    )


def _fvg_fill_price_local(
    bar: CapitalizerM1Bar,
    *,
    fvg_low: Decimal,
    fvg_high: Decimal,
    side: CapitalizerSide,
) -> Decimal | None:
    if bar.high < fvg_low or bar.low > fvg_high:
        return None
    if fvg_low <= bar.open <= fvg_high:
        return bar.open
    if side is CapitalizerSide.LONG:
        if bar.open > fvg_high and bar.low <= fvg_high:
            return fvg_high
        return None
    if bar.open < fvg_low and bar.high >= fvg_low:
        return fvg_low
    return None


def _scan_session(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_date: str,
    bars: tuple[CapitalizerM1Bar, ...],
    bias: HTFBiasEvent,
    objective_source: DailyObjective,
    stages: Counter[str],
) -> tuple[ICTScannerTrade, ...]:
    if len(bars) < 7:
        stages["SESSION_TOO_SPARSE"] += 1
        return ()

    side = (
        CapitalizerSide.LONG
        if bias.direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSide.SHORT
    )
    objective = (
        objective_source.high
        if side is CapitalizerSide.LONG
        else objective_source.low
    )
    session_open = bars[0].open
    if (
        (side is CapitalizerSide.LONG and objective <= session_open)
        or (side is CapitalizerSide.SHORT and objective >= session_open)
    ):
        stages["OBJECTIVE_WRONG_SIDE_AT_SESSION_OPEN"] += 1
        return ()

    high_pivots, low_pivots = _confirmed_pivots(bars)
    raid_pivots = low_pivots if side is CapitalizerSide.LONG else high_pivots
    mss_pivots = high_pivots if side is CapitalizerSide.LONG else low_pivots

    result: list[ICTScannerTrade] = []
    raid_index: int | None = None
    raid_extreme: Decimal | None = None
    swept_pivot_price: Decimal | None = None
    swept_pivot_index: int | None = None
    pending: ICTScannerSetup | None = None

    index = 2
    while index < len(bars):
        bar = bars[index]

        if _objective_touched(bar, side=side, objective=objective):
            stages["OBJECTIVE_CONSUMED"] += 1
            break

        latest_raid_pivot = _latest_pivot(raid_pivots, before_index=index)
        if latest_raid_pivot is not None:
            pivot_index, pivot_price = latest_raid_pivot
            swept = (
                bar.low < pivot_price
                if side is CapitalizerSide.LONG
                else bar.high > pivot_price
            )
            if swept:
                stages["M1_RAID"] += 1
                raid_index = index
                raid_extreme = (
                    bar.low if side is CapitalizerSide.LONG else bar.high
                )
                swept_pivot_price = pivot_price
                swept_pivot_index = pivot_index
                pending = None
                index += 1
                continue

        # Confirm FVG one bar after the displacement candle. A newer raid on
        # the confirmation bar has already reset the state above.
        displacement_index = index - 1
        if (
            raid_index is not None
            and raid_extreme is not None
            and swept_pivot_price is not None
            and swept_pivot_index is not None
            and pending is None
            and displacement_index > raid_index
        ):
            displacement = bars[displacement_index]
            if _significant_displacement(displacement, side=side):
                stages["M1_DISPLACEMENT_AFTER_RAID"] += 1
                latest_mss = _latest_pivot(
                    mss_pivots,
                    before_index=displacement_index,
                )
                if latest_mss is not None:
                    _, mss_level = latest_mss
                    mss_confirmed = (
                        displacement.close > mss_level
                        if side is CapitalizerSide.LONG
                        else displacement.close < mss_level
                    )
                    if mss_confirmed:
                        stages["M1_MSS_AFTER_RAID"] += 1
                        first = bars[displacement_index - 1]
                        third = bar
                        if side is CapitalizerSide.LONG:
                            fvg_valid = first.high < third.low
                            fvg_low, fvg_high = first.high, third.low
                        else:
                            fvg_valid = first.low > third.high
                            fvg_low, fvg_high = third.high, first.low
                        if fvg_valid:
                            stages["M1_FVG_AFTER_MSS"] += 1
                            pending = ICTScannerSetup(
                                raid_index=raid_index,
                                raid_extreme=raid_extreme,
                                swept_pivot_price=swept_pivot_price,
                                swept_pivot_index=swept_pivot_index,
                                displacement_index=displacement_index,
                                fvg_confirm_index=index,
                                mss_level=mss_level,
                                fvg_low=fvg_low,
                                fvg_high=fvg_high,
                            )

        if pending is not None and index > pending.fvg_confirm_index:
            fill = _fvg_fill_price_local(
                bar,
                fvg_low=pending.fvg_low,
                fvg_high=pending.fvg_high,
                side=side,
            )
            if fill is not None:
                valid_geometry = (
                    pending.raid_extreme < fill < objective
                    if side is CapitalizerSide.LONG
                    else objective < fill < pending.raid_extreme
                )
                if not valid_geometry:
                    stages["ENTRY_STOP_TARGET_GEOMETRY_INVALID"] += 1
                    pending = None
                    raid_index = None
                    raid_extreme = None
                    swept_pivot_price = None
                    swept_pivot_index = None
                    index += 1
                    continue

                stages["M1_RETRACE_ENTRY"] += 1
                realized, exit_reason, held, ambiguous, exit_at = _lifecycle(
                    bars,
                    entry_index=index,
                    side=side,
                    entry_price=fill,
                    stop_price=pending.raid_extreme,
                    target_price=objective,
                )
                risk = abs(fill - pending.raid_extreme)
                if risk <= 0:
                    stages["NONPOSITIVE_RISK"] += 1
                    pending = None
                    index += 1
                    continue

                bias_age = int(
                    (
                        bars[index].opened_at - bias.confirmed_at
                    ).total_seconds()
                    // 60
                )
                result.append(
                    ICTScannerTrade(
                        symbol=symbol,
                        session=session.value,
                        operating_date=operating_date,
                        side=side.value,
                        htf_bias_confirmed_at=bias.confirmed_at.isoformat(),
                        htf_bias_age_minutes=bias_age,
                        htf_closure_kind=bias.closure_kind,
                        htf_poi_kind=bias.poi_kind,
                        objective_source_date=objective_source.ny_date,
                        objective_price=str(objective),
                        raid_at=bars[pending.raid_index].opened_at.isoformat(),
                        swept_pivot_price=str(pending.swept_pivot_price),
                        raid_extreme=str(pending.raid_extreme),
                        displacement_at=bars[
                            pending.displacement_index
                        ].closed_at.isoformat(),
                        mss_level=str(pending.mss_level),
                        fvg_confirmed_at=bars[
                            pending.fvg_confirm_index
                        ].closed_at.isoformat(),
                        fvg_low=str(pending.fvg_low),
                        fvg_high=str(pending.fvg_high),
                        entry_at=bar.opened_at.isoformat(),
                        exit_at=exit_at.isoformat(),
                        entry_price=str(fill),
                        stop_price=str(pending.raid_extreme),
                        target_price=str(objective),
                        planned_reward_r=str(abs(objective - fill) / risk),
                        realized_gross_r=str(realized),
                        exit_reason=exit_reason,
                        m1_bars_held=held,
                        same_minute_stop_target_ambiguity=ambiguous,
                    )
                )

                exit_index = next(
                    (
                        idx
                        for idx in range(index, len(bars))
                        if bars[idx].closed_at >= exit_at
                    ),
                    len(bars) - 1,
                )
                if exit_reason == "TARGET":
                    break
                index = exit_index + 1
                raid_index = None
                raid_extreme = None
                swept_pivot_price = None
                swept_pivot_index = None
                pending = None
                continue

        index += 1

    return tuple(result)

def _group_operating_sessions(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
) -> dict[str, tuple[CapitalizerM1Bar, ...]]:
    grouped: dict[str, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        if not (WINDOW_START <= bar.opened_at < WINDOW_END):
            continue
        if capitalizer_session_at(bar.opened_at) is not session:
            continue
        grouped[_operating_date(bar.opened_at, session)].append(bar)
    return {
        key: tuple(sorted(chunk, key=lambda item: item.opened_at))
        for key, chunk in grouped.items()
    }


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[ICTScannerMarketReport, tuple[ICTScannerTrade, ...]]:
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not bars:
        raise ValueError("full ICT scanner found no native M1 data")
    symbol = bars[0].symbol
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("one scanner root must contain one symbol")

    h1 = _aggregate_h1(bars)
    bias_events = _build_htf_bias_events(h1)
    event_times = tuple(item.confirmed_at for item in bias_events)
    objectives = _daily_objectives(bars)
    objective_days = tuple(item.ny_date for item in objectives)
    sessions = _group_operating_sessions(bars, session=session)
    if not sessions:
        raise ValueError("full ICT scanner found no operating sessions")

    stages: Counter[str] = Counter()
    trades: list[ICTScannerTrade] = []
    sessions_with_bias = 0
    sessions_without_bias = 0
    sessions_with_objective = 0
    wrong_side = 0
    raw_counts: Counter[str] = Counter()

    for operating_date, session_bars in sorted(sessions.items()):
        start = session_bars[0].opened_at
        bias = _latest_bias_before(bias_events, event_times, start)
        if bias is None:
            sessions_without_bias += 1
            stages["HTF_BIAS_UNAVAILABLE"] += 1
            continue
        sessions_with_bias += 1
        objective = _latest_completed_objective(
            objectives,
            objective_days,
            start,
        )
        if objective is None:
            stages["STRUCTURAL_OBJECTIVE_UNAVAILABLE"] += 1
            continue
        sessions_with_objective += 1
        before = stages["OBJECTIVE_WRONG_SIDE_AT_SESSION_OPEN"]
        produced = _scan_session(
            symbol=symbol,
            session=session,
            operating_date=operating_date,
            bars=session_bars,
            bias=bias,
            objective_source=objective,
            stages=stages,
        )
        if stages["OBJECTIVE_WRONG_SIDE_AT_SESSION_OPEN"] > before:
            wrong_side += 1
        trades.extend(produced)
        raw_counts[operating_date] += len(produced)

    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    metrics = _scanner_metrics(ordered)
    report = ICTScannerMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        operating_sessions_scanned=len(sessions),
        sessions_with_htf_bias=sessions_with_bias,
        sessions_without_htf_bias=sessions_without_bias,
        sessions_with_objective=sessions_with_objective,
        sessions_objective_wrong_side_at_open=wrong_side,
        m1_raid_events=stages["M1_RAID"],
        m1_displacement_events_after_raid=stages["M1_DISPLACEMENT_AFTER_RAID"],
        m1_mss_events_after_raid=stages["M1_MSS_AFTER_RAID"],
        m1_fvg_events_after_mss=stages["M1_FVG_AFTER_MSS"],
        m1_retrace_entries_raw=len(ordered),
        raw_metrics=metrics,
        raw_stop_exits=sum(item.exit_reason == "STOP" for item in ordered),
        raw_target_exits=sum(item.exit_reason == "TARGET" for item in ordered),
        raw_session_exits=sum(item.exit_reason == "SESSION_EXIT" for item in ordered),
        sessions_with_raw_entry=sum(count > 0 for count in raw_counts.values()),
        sessions_over_max3_market_raw=sum(
            count > MAX_EXECUTIONS_PER_SESSION for count in raw_counts.values()
        ),
        max_raw_entries_one_market_session=max(raw_counts.values(), default=0),
        stage_rejections=tuple(
            sorted(stages.items(), key=lambda item: (-item[1], item[0]))
        ),
    )
    return report, ordered


def _scanner_metrics(
    trades: tuple[ICTScannerTrade, ...],
) -> ICTReplayMetrics | None:
    if not trades:
        return None
    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    values = tuple(Decimal(item.realized_gross_r) for item in ordered)
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
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
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=None if gross_loss == 0 else str(gross_profit / gross_loss),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=sum(item.exit_reason == "STOP" for item in ordered),
        target_exits=sum(item.exit_reason == "TARGET" for item in ordered),
        session_exits=sum(item.exit_reason == "SESSION_EXIT" for item in ordered),
        ambiguous_stop_first_exits=sum(
            item.same_minute_stop_target_ambiguity for item in ordered
        ),
    )


def write_market(
    report: ICTScannerMarketReport,
    trades: tuple[ICTScannerTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-full-ict-density-scanner-1y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-full-ict-density-scanner-1y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"full ICT density matrix requires 9 reports, got {len(paths)}")
    reports: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("market scanner report must be object")
        reports.append(dict(raw))
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("full ICT density universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def _load_all_trades(root: Path) -> tuple[ICTScannerTrade, ...]:
    rows: list[ICTScannerTrade] = []
    for path in sorted(root.rglob("capitalizer-*-full-ict-density-scanner-1y-v1-trades.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(ICTScannerTrade(**json.loads(line)))
    return tuple(sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol)))


def _portfolio_max3(
    trades: tuple[ICTScannerTrade, ...],
) -> tuple[ICTScannerTrade, ...]:
    grouped: dict[str, list[ICTScannerTrade]] = defaultdict(list)
    for trade in trades:
        key = f"{trade.session}:{trade.operating_date}"
        grouped[key].append(trade)
    selected: list[ICTScannerTrade] = []
    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=lambda item: (_aware(item.entry_at), item.symbol))
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol)))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    all_trades = _load_all_trades(root)
    max3 = _portfolio_max3(all_trades)
    raw_metrics = _scanner_metrics(all_trades)
    max3_metrics = _scanner_metrics(max3)

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        raw = tuple(item for item in all_trades if item.session == session.value)
        capped = tuple(item for item in max3 if item.session == session.value)
        per_session[session.value] = {
            "raw_trades": len(raw),
            "raw_metrics": (
                None if (metrics := _scanner_metrics(raw)) is None else asdict(metrics)
            ),
            "max3_trades": len(capped),
            "max3_metrics": (
                None if (metrics := _scanner_metrics(capped)) is None else asdict(metrics)
            ),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "entry_identity": ENTRY_IDENTITY,
        "htf_context_identity": HTF_CONTEXT_IDENTITY,
        "objective_identity": OBJECTIVE_IDENTITY,
        "stop_identity": STOP_IDENTITY,
        "target_identity": TARGET_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "operating_sessions_scanned": sum(
            int(item["operating_sessions_scanned"]) for item in reports
        ),
        "sessions_with_htf_bias": sum(
            int(item["sessions_with_htf_bias"]) for item in reports
        ),
        "sessions_without_htf_bias": sum(
            int(item["sessions_without_htf_bias"]) for item in reports
        ),
        "m1_raid_events": sum(int(item["m1_raid_events"]) for item in reports),
        "m1_displacement_events_after_raid": sum(
            int(item["m1_displacement_events_after_raid"]) for item in reports
        ),
        "m1_mss_events_after_raid": sum(
            int(item["m1_mss_events_after_raid"]) for item in reports
        ),
        "m1_fvg_events_after_mss": sum(
            int(item["m1_fvg_events_after_mss"]) for item in reports
        ),
        "raw_trades": len(all_trades),
        "raw_metrics": None if raw_metrics is None else asdict(raw_metrics),
        "raw_stop_exits": sum(item.exit_reason == "STOP" for item in all_trades),
        "raw_target_exits": sum(item.exit_reason == "TARGET" for item in all_trades),
        "raw_session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in all_trades
        ),
        "max3_selected_trades": len(max3),
        "max3_metrics": None if max3_metrics is None else asdict(max3_metrics),
        "max3_stop_exits": sum(item.exit_reason == "STOP" for item in max3),
        "max3_target_exits": sum(item.exit_reason == "TARGET" for item in max3),
        "max3_session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in max3
        ),
        "per_session": per_session,
        "markets": reports,
        "old_candidate_ledger_used": False,
        "old_raid_rejection_gate_used": False,
        "htf_context_changed_from_frozen_capitalizer_route": False,
        "order_block_required": False,
        "qore_session_bucket_is_ict_killzone": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-full-ict-density-scanner-1y-matrix-v1.json"
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
                    "raw_trades": report.m1_retrace_entries_raw,
                    "pf": None if report.raw_metrics is None else report.raw_metrics.profit_factor,
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
