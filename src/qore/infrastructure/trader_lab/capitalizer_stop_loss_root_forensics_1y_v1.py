"""Root-cause forensics for the full-density Capitalizer ICT scanner.

This laboratory does not change entries, stops, targets, sizing or admission.
It enriches the already-consumed 1Y corpus of 5,252 trades with causal features
available at entry time and with post-entry path diagnostics.

Primary questions:
1. Did the trade reach a nearer causal liquidity objective or 2R before the
   original raid-extreme stop?
2. Was the original stop a wick-only breach that reclaimed, or did price close
   through structural invalidation?
3. Was the swept level a previous-day/session/M15/M5 level or only an M1 pivot?
4. Was the displacement materially strong relative to its prior M1 context?
5. Was the MSS level also visible on M5/M15?
6. How did time-of-day, bias age and parent-timeframe state stratify outcomes?

No threshold or cohort in this module is eligible for promotion. Cohorts are
descriptive/falsification evidence over an already-consumed window.

Window:
    [2025-09-17, 2026-09-17)

Research only. No live, production, certification or real-capital authorization.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    IDENTITY as SCANNER_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    WINDOW_END,
    WINDOW_START,
    _aware,
    _operating_date,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at

IDENTITY = "QORE_CAPITALIZER_STOP_LOSS_ROOT_FORENSICS_1Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STOP_LOSS_ROOT_FORENSICS_1Y_MATRIX_V1"
LOOKBACK_START = WINDOW_START - timedelta(days=45)
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
class AggregateBar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class Pivot:
    occurred_at: datetime
    confirmed_at: datetime
    price: Decimal
    kind: str


@dataclass(frozen=True, slots=True)
class SessionExtreme:
    session: str
    operating_date: str
    opened_at: datetime
    closed_at: datetime
    high: Decimal
    low: Decimal


@dataclass(frozen=True, slots=True)
class DailyExtreme:
    ny_date: str
    high: Decimal
    low: Decimal


@dataclass(frozen=True, slots=True)
class TradeForensics:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    exit_at: str
    original_exit_reason: str
    original_realized_r: str
    original_planned_reward_r: str
    entry_price: str
    original_stop_price: str
    original_macro_target_price: str

    ny_entry_hour: int
    ny_entry_minute: int
    session_elapsed_minutes: int
    session_remaining_minutes: int
    htf_bias_age_minutes: int

    raid_at: str
    swept_pivot_price: str
    raid_extreme: str
    raid_depth_r: str
    raid_close_back_inside: bool
    liquidity_level_class: str
    liquidity_level_distance_provider_increments: str

    displacement_at: str
    displacement_body_ratio: str
    displacement_range_r: str
    displacement_body_r: str
    displacement_range_vs_prior20_median: str | None
    displacement_body_vs_prior20_median: str | None

    mss_level: str
    mss_break_close_r: str
    mss_level_visible_m5: bool
    mss_level_visible_m15: bool

    fvg_low: str
    fvg_high: str
    fvg_width_r: str
    fvg_entry_depth_fraction: str
    fvg_far_edge: str

    m15_parent_state: str
    h1_parent_state: str
    h4_parent_state: str
    m15_range_position: str | None

    protected_swing_price: str | None
    protected_swing_distance_r: str | None

    nearest_causal_liquidity_price: str | None
    nearest_causal_liquidity_type: str | None
    nearest_causal_liquidity_r: str | None
    two_r_price: str

    nearest_liquidity_before_original_stop: bool | None
    two_r_before_original_stop: bool
    macro_target_before_original_stop: bool
    nearest_liquidity_after_stop_before_session_end: bool | None
    two_r_after_stop_before_session_end: bool
    macro_target_after_stop_before_session_end: bool

    original_stop_wick_only_reclaim: bool
    raid_extreme_close_invalidated_before_session_end: bool
    fvg_far_edge_close_invalidated_before_original_stop: bool
    protected_swing_touched_before_original_stop: bool | None
    protected_swing_close_invalidated_before_original_stop: bool | None

    outcome_used_for_feature_selection: bool = False


@dataclass(frozen=True, slots=True)
class CohortSummary:
    cohort: str
    trades: int
    stops: int
    targets: int
    session_exits: int
    stop_rate: str
    target_rate: str
    total_r: str
    mean_r: str
    profit_factor: str | None


@dataclass(frozen=True, slots=True)
class MarketForensicsReport:
    identity: str
    source_identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    source_trades: int
    source_stops: int
    source_targets: int
    source_session_exits: int

    stop_trades_nearest_liquidity_before_stop: int
    stop_trades_two_r_before_stop: int
    stop_trades_wick_only_reclaim: int
    stop_trades_fvg_close_invalidated_before_stop: int
    stop_trades_protected_swing_survived_stop: int
    stop_trades_macro_target_after_stop_same_session: int

    liquidity_class_cohorts: tuple[CohortSummary, ...]
    ny_hour_cohorts: tuple[CohortSummary, ...]
    planned_rr_cohorts: tuple[CohortSummary, ...]
    bias_age_cohorts: tuple[CohortSummary, ...]
    displacement_body_cohorts: tuple[CohortSummary, ...]
    displacement_relative_range_cohorts: tuple[CohortSummary, ...]
    m15_parent_cohorts: tuple[CohortSummary, ...]

    methodology_changed: bool = False
    entries_changed: bool = False
    stop_changed: bool = False
    target_changed: bool = False
    filters_applied: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _load_source_trades(root: Path) -> tuple[dict[str, Any], ...]:
    reports = sorted(root.rglob("capitalizer-*-full-ict-density-scanner-1y-v1.json"))
    ledgers = sorted(
        root.rglob("capitalizer-*-full-ict-density-scanner-1y-v1-trades.jsonl")
    )
    if len(reports) != 1 or len(ledgers) != 1:
        raise ValueError("root forensics requires one scanner report and one ledger")
    report_raw: Any = json.loads(reports[0].read_text(encoding="utf-8"))
    if not isinstance(report_raw, dict) or report_raw.get("identity") != SCANNER_IDENTITY:
        raise ValueError("unexpected full-density scanner identity")
    rows: list[dict[str, Any]] = []
    with ledgers[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw: Any = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("scanner trade row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("root forensics rejects outcome-selected source rows")
            rows.append(dict(raw))
    if not rows:
        raise ValueError("root forensics source ledger is empty")
    return tuple(rows)


def _load_m1(root: Path) -> tuple[CapitalizerM1Bar, ...]:
    rows = tuple(
        bar
        for bar in iter_cibo_m1(root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not rows:
        raise ValueError("root forensics found no native M1 evidence")
    return rows


def _aggregate(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    minutes: int,
) -> tuple[AggregateBar, ...]:
    if minutes <= 0:
        raise ValueError("aggregate minutes must be positive")
    grouped: dict[datetime, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        local = bar.opened_at.astimezone(NEW_YORK)
        floored_minute = (local.minute // minutes) * minutes
        key_local = local.replace(
            minute=floored_minute,
            second=0,
            microsecond=0,
        )
        grouped[key_local.astimezone(bar.opened_at.tzinfo)].append(bar)
    result: list[AggregateBar] = []
    for key in sorted(grouped):
        chunk = sorted(grouped[key], key=lambda item: item.opened_at)
        required = max(1, int(minutes * Decimal("0.75")))
        if len(chunk) < required:
            continue
        result.append(
            AggregateBar(
                opened_at=chunk[0].opened_at,
                closed_at=chunk[-1].closed_at,
                open=chunk[0].open,
                high=max(item.high for item in chunk),
                low=min(item.low for item in chunk),
                close=chunk[-1].close,
            )
        )
    return tuple(result)


def _aggregate_higher(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    hours: int,
) -> tuple[AggregateBar, ...]:
    grouped: dict[tuple[int, int, int, int, int], list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        local = bar.opened_at.astimezone(NEW_YORK)
        block_hour = (local.hour // hours) * hours
        offset = local.utcoffset()
        if offset is None:
            raise ValueError("NY-local bar requires offset")
        key = (
            local.year,
            local.month,
            local.day,
            block_hour,
            int(offset.total_seconds()),
        )
        grouped[key].append(bar)
    result: list[AggregateBar] = []
    minimum = hours * 60 * 3 // 4
    for key in sorted(grouped):
        chunk = sorted(grouped[key], key=lambda item: item.opened_at)
        if len(chunk) < minimum:
            continue
        result.append(
            AggregateBar(
                opened_at=chunk[0].opened_at,
                closed_at=chunk[-1].closed_at,
                open=chunk[0].open,
                high=max(item.high for item in chunk),
                low=min(item.low for item in chunk),
                close=chunk[-1].close,
            )
        )
    return tuple(result)


def _pivots(bars: tuple[AggregateBar, ...]) -> tuple[Pivot, ...]:
    result: list[Pivot] = []
    for center in range(1, len(bars) - 1):
        left, mid, right = bars[center - 1], bars[center], bars[center + 1]
        if mid.high > left.high and mid.high > right.high:
            result.append(
                Pivot(
                    occurred_at=mid.opened_at,
                    confirmed_at=right.closed_at,
                    price=mid.high,
                    kind="HIGH",
                )
            )
        if mid.low < left.low and mid.low < right.low:
            result.append(
                Pivot(
                    occurred_at=mid.opened_at,
                    confirmed_at=right.closed_at,
                    price=mid.low,
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


def _session_extremes(
    bars: tuple[CapitalizerM1Bar, ...],
) -> tuple[SessionExtreme, ...]:
    grouped: dict[tuple[str, str], list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        session = capitalizer_session_at(bar.opened_at)
        if session is None:
            continue
        op_date = _operating_date(bar.opened_at, session)
        grouped[(session.value, op_date)].append(bar)
    result: list[SessionExtreme] = []
    for (session, op_date), chunk in grouped.items():
        ordered = sorted(chunk, key=lambda item: item.opened_at)
        result.append(
            SessionExtreme(
                session=session,
                operating_date=op_date,
                opened_at=ordered[0].opened_at,
                closed_at=ordered[-1].closed_at,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
            )
        )
    return tuple(sorted(result, key=lambda item: item.closed_at))


def _daily_extremes(
    bars: tuple[CapitalizerM1Bar, ...],
) -> tuple[DailyExtreme, ...]:
    grouped: dict[str, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        day = bar.opened_at.astimezone(NEW_YORK).date().isoformat()
        grouped[day].append(bar)
    result = [
        DailyExtreme(
            ny_date=day,
            high=max(item.high for item in chunk),
            low=min(item.low for item in chunk),
        )
        for day, chunk in grouped.items()
        if len(chunk) >= 60
    ]
    return tuple(sorted(result, key=lambda item: item.ny_date))


def _nearest_bar_index(
    times: tuple[datetime, ...],
    moment: datetime,
) -> int:
    index = bisect.bisect_left(times, moment)
    if index >= len(times):
        return len(times) - 1
    return index


def _latest_completed_bar(
    bars: tuple[AggregateBar, ...],
    closes: tuple[datetime, ...],
    moment: datetime,
) -> int | None:
    index = bisect.bisect_right(closes, moment) - 1
    return None if index < 0 else index


def _structure_state(
    bars: tuple[AggregateBar, ...],
    pivots: tuple[Pivot, ...],
    moment: datetime,
) -> str:
    completed = [bar for bar in bars if bar.closed_at <= moment]
    if not completed:
        return "UNAVAILABLE"
    available = [pivot for pivot in pivots if pivot.confirmed_at <= moment]
    highs = [pivot for pivot in available if pivot.kind == "HIGH"]
    lows = [pivot for pivot in available if pivot.kind == "LOW"]
    if not highs or not lows:
        return "UNAVAILABLE"
    close = completed[-1].close
    if close > highs[-1].price:
        return "BULLISH_BREAK"
    if close < lows[-1].price:
        return "BEARISH_BREAK"
    return "RANGE"


def _aligned_state(state: str, side: CapitalizerSide) -> str:
    if state == "UNAVAILABLE":
        return state
    if state == "RANGE":
        return "RANGE"
    if side is CapitalizerSide.LONG:
        return "ALIGNED" if state == "BULLISH_BREAK" else "OPPOSED"
    return "ALIGNED" if state == "BEARISH_BREAK" else "OPPOSED"


def _range_position(
    bars: tuple[AggregateBar, ...],
    closes: tuple[datetime, ...],
    moment: datetime,
    price: Decimal,
    *,
    lookback: int = 20,
) -> Decimal | None:
    index = _latest_completed_bar(bars, closes, moment)
    if index is None:
        return None
    chunk = bars[max(0, index - lookback + 1) : index + 1]
    if len(chunk) < 5:
        return None
    low = min(item.low for item in chunk)
    high = max(item.high for item in chunk)
    if high <= low:
        return None
    return (price - low) / (high - low)


def _previous_daily(
    days: tuple[DailyExtreme, ...],
    moment: datetime,
) -> DailyExtreme | None:
    local_day = moment.astimezone(NEW_YORK).date().isoformat()
    available = [item for item in days if item.ny_date < local_day]
    return None if not available else available[-1]


def _previous_session(
    sessions: tuple[SessionExtreme, ...],
    moment: datetime,
) -> SessionExtreme | None:
    available = [item for item in sessions if item.closed_at < moment]
    return None if not available else available[-1]


def _matching_pivot(
    pivots: tuple[Pivot, ...],
    *,
    moment: datetime,
    price: Decimal,
    kind: str,
    tolerance: Decimal,
) -> bool:
    for pivot in reversed(pivots):
        if pivot.confirmed_at > moment:
            continue
        if pivot.kind != kind:
            continue
        if abs(pivot.price - price) <= tolerance:
            return True
    return False


def _liquidity_class(
    *,
    swept_price: Decimal,
    raid_at: datetime,
    side: CapitalizerSide,
    previous_day: DailyExtreme | None,
    previous_session: SessionExtreme | None,
    m5_pivots: tuple[Pivot, ...],
    m15_pivots: tuple[Pivot, ...],
    tolerance: Decimal,
) -> tuple[str, Decimal]:
    kind = "LOW" if side is CapitalizerSide.LONG else "HIGH"
    if previous_day is not None:
        level = previous_day.low if kind == "LOW" else previous_day.high
        distance = abs(swept_price - level)
        if distance <= tolerance:
            return "PREVIOUS_NY_DAY_EXTREME", distance / tolerance
    if previous_session is not None:
        level = previous_session.low if kind == "LOW" else previous_session.high
        distance = abs(swept_price - level)
        if distance <= tolerance:
            return "PRIOR_RESEARCH_SESSION_EXTREME", distance / tolerance
    if _matching_pivot(
        m15_pivots,
        moment=raid_at,
        price=swept_price,
        kind=kind,
        tolerance=tolerance,
    ):
        return "M15_CONFIRMED_SWING", Decimal("0")
    if _matching_pivot(
        m5_pivots,
        moment=raid_at,
        price=swept_price,
        kind=kind,
        tolerance=tolerance,
    ):
        return "M5_CONFIRMED_SWING", Decimal("0")
    return "M1_ONLY_PIVOT", Decimal("0")


def _candidate_liquidity_levels(
    *,
    entry_at: datetime,
    entry: Decimal,
    side: CapitalizerSide,
    previous_day: DailyExtreme | None,
    previous_session: SessionExtreme | None,
    m5_pivots: tuple[Pivot, ...],
    m15_pivots: tuple[Pivot, ...],
) -> tuple[tuple[Decimal, str], ...]:
    candidates: list[tuple[Decimal, str]] = []
    if previous_day is not None:
        price = previous_day.high if side is CapitalizerSide.LONG else previous_day.low
        if (side is CapitalizerSide.LONG and price > entry) or (
            side is CapitalizerSide.SHORT and price < entry
        ):
            candidates.append((price, "PREVIOUS_NY_DAY_EXTREME"))
    if previous_session is not None:
        price = (
            previous_session.high
            if side is CapitalizerSide.LONG
            else previous_session.low
        )
        if (side is CapitalizerSide.LONG and price > entry) or (
            side is CapitalizerSide.SHORT and price < entry
        ):
            candidates.append((price, "PRIOR_RESEARCH_SESSION_EXTREME"))

    desired = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    for label, pivots in (("M15_SWING", m15_pivots), ("M5_SWING", m5_pivots)):
        for pivot in pivots:
            if pivot.confirmed_at > entry_at or pivot.kind != desired:
                continue
            if (side is CapitalizerSide.LONG and pivot.price > entry) or (
                side is CapitalizerSide.SHORT and pivot.price < entry
            ):
                candidates.append((pivot.price, label))
    if not candidates:
        return ()
    return tuple(
        sorted(
            candidates,
            key=lambda item: abs(item[0] - entry),
        )
    )


def _protected_swing(
    pivots: tuple[Pivot, ...],
    *,
    raid_at: datetime,
    entry_at: datetime,
    side: CapitalizerSide,
    entry: Decimal,
) -> Decimal | None:
    desired = "LOW" if side is CapitalizerSide.LONG else "HIGH"
    available = [
        pivot
        for pivot in pivots
        if raid_at <= pivot.occurred_at
        and pivot.confirmed_at <= entry_at
        and pivot.kind == desired
        and (
            (side is CapitalizerSide.LONG and pivot.price < entry)
            or (side is CapitalizerSide.SHORT and pivot.price > entry)
        )
    ]
    return None if not available else available[-1].price


def _session_bounds(session: CapitalizerSession, moment: datetime) -> tuple[datetime, datetime]:
    op_date = datetime.fromisoformat(_operating_date(moment, session)).date()
    if session is CapitalizerSession.ASIA:
        start = datetime.combine(op_date, datetime.min.time(), tzinfo=NEW_YORK).replace(hour=20)
        end = start + timedelta(hours=6)
    elif session is CapitalizerSession.LONDON:
        start = datetime.combine(op_date, datetime.min.time(), tzinfo=NEW_YORK).replace(hour=2)
        end = start + timedelta(hours=6, minutes=30)
    else:
        start = datetime.combine(op_date, datetime.min.time(), tzinfo=NEW_YORK).replace(
            hour=8, minute=30
        )
        end = start + timedelta(hours=7, minutes=30)
    return start.astimezone(moment.tzinfo), end.astimezone(moment.tzinfo)


def _bar_touches(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    price: Decimal,
) -> bool:
    return bar.high >= price if side is CapitalizerSide.LONG else bar.low <= price


def _bar_stop_touches(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    stop: Decimal,
) -> bool:
    return bar.low <= stop if side is CapitalizerSide.LONG else bar.high >= stop


def _close_invalidates(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    level: Decimal,
) -> bool:
    return bar.close < level if side is CapitalizerSide.LONG else bar.close > level


def _first_touch_index(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    price: Decimal,
) -> int | None:
    for index, bar in enumerate(bars):
        if _bar_touches(bar, side=side, price=price):
            return index
    return None


def _first_stop_index(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    stop: Decimal,
) -> int | None:
    for index, bar in enumerate(bars):
        if _bar_stop_touches(bar, side=side, stop=stop):
            return index
    return None


def _before_stop(target_index: int | None, stop_index: int | None) -> bool:
    if target_index is None:
        return False
    if stop_index is None:
        return True
    return target_index < stop_index


def _after_stop(target_index: int | None, stop_index: int | None) -> bool:
    if target_index is None or stop_index is None:
        return False
    return target_index > stop_index


def _cohort_metrics(label: str, rows: list[TradeForensics]) -> CohortSummary:
    values = tuple(Decimal(item.original_realized_r) for item in rows)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    total = sum(values, Decimal("0"))
    count = len(rows)
    return CohortSummary(
        cohort=label,
        trades=count,
        stops=sum(item.original_exit_reason == "STOP" for item in rows),
        targets=sum(item.original_exit_reason == "TARGET" for item in rows),
        session_exits=sum(item.original_exit_reason == "SESSION_EXIT" for item in rows),
        stop_rate="0" if count == 0 else str(
            Decimal(sum(item.original_exit_reason == "STOP" for item in rows))
            / Decimal(count)
        ),
        target_rate="0" if count == 0 else str(
            Decimal(sum(item.original_exit_reason == "TARGET" for item in rows))
            / Decimal(count)
        ),
        total_r=str(total),
        mean_r=str(total / Decimal(count)),
        profit_factor=None if gl == 0 else str(gp / gl),
    )


def _cohorts(
    rows: tuple[TradeForensics, ...],
    *,
    selector: Any,
) -> tuple[CohortSummary, ...]:
    grouped: dict[str, list[TradeForensics]] = defaultdict(list)
    for row in rows:
        grouped[str(selector(row))].append(row)
    return tuple(
        _cohort_metrics(key, grouped[key])
        for key in sorted(grouped)
    )


def _rr_bin(value: Decimal) -> str:
    if value < 3:
        return "RR_LT_3"
    if value < 5:
        return "RR_3_5"
    if value < 8:
        return "RR_5_8"
    if value < 12:
        return "RR_8_12"
    if value < 20:
        return "RR_12_20"
    if value < 40:
        return "RR_20_40"
    return "RR_40_PLUS"


def _bias_age_bin(minutes: int) -> str:
    hours = Decimal(minutes) / Decimal("60")
    if hours < 2:
        return "AGE_LT_2H"
    if hours < 4:
        return "AGE_2_4H"
    if hours < 6:
        return "AGE_4_6H"
    if hours < 8:
        return "AGE_6_8H"
    if hours < 12:
        return "AGE_8_12H"
    if hours < 24:
        return "AGE_12_24H"
    return "AGE_24H_PLUS"


def _body_bin(value: Decimal) -> str:
    if value < Decimal("0.5"):
        return "BODY_LT_0_50"
    if value < Decimal("0.6"):
        return "BODY_0_50_0_60"
    if value < Decimal("0.7"):
        return "BODY_0_60_0_70"
    if value < Decimal("0.8"):
        return "BODY_0_70_0_80"
    return "BODY_0_80_PLUS"


def _relative_bin(value: Decimal | None) -> str:
    if value is None:
        return "REL_UNAVAILABLE"
    if value < 1:
        return "REL_LT_1"
    if value < Decimal("1.5"):
        return "REL_1_1_5"
    if value < 2:
        return "REL_1_5_2"
    return "REL_2_PLUS"


def _enrich_trade(
    raw: dict[str, Any],
    *,
    bars: tuple[CapitalizerM1Bar, ...],
    bar_times: tuple[datetime, ...],
    m1_pivots: tuple[Pivot, ...],
    m5_pivots: tuple[Pivot, ...],
    m15_bars: tuple[AggregateBar, ...],
    m15_closes: tuple[datetime, ...],
    m15_pivots: tuple[Pivot, ...],
    h1_bars: tuple[AggregateBar, ...],
    h1_pivots: tuple[Pivot, ...],
    h4_bars: tuple[AggregateBar, ...],
    h4_pivots: tuple[Pivot, ...],
    sessions: tuple[SessionExtreme, ...],
    days: tuple[DailyExtreme, ...],
) -> TradeForensics:
    symbol = str(raw["symbol"])
    session = CapitalizerSession(str(raw["session"]))
    side = CapitalizerSide(str(raw["side"]))
    entry_at = _aware(str(raw["entry_at"]))
    raid_at = _aware(str(raw["raid_at"]))
    displacement_at = _aware(str(raw["displacement_at"]))
    entry = Decimal(str(raw["entry_price"]))
    stop = Decimal(str(raw["stop_price"]))
    macro = Decimal(str(raw["target_price"]))
    swept = Decimal(str(raw["swept_pivot_price"]))
    raid_extreme = Decimal(str(raw["raid_extreme"]))
    mss = Decimal(str(raw["mss_level"]))
    fvg_low = Decimal(str(raw["fvg_low"]))
    fvg_high = Decimal(str(raw["fvg_high"]))
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("root forensics requires positive risk")

    entry_index = _nearest_bar_index(bar_times, entry_at)
    raid_index = _nearest_bar_index(bar_times, raid_at)
    displacement_index = max(0, bisect.bisect_left(bar_times, displacement_at) - 1)
    displacement_bar = bars[displacement_index]
    raid_bar = bars[raid_index]
    tolerance = Decimal(1).scaleb(-raid_bar.digits)

    prior_start = max(0, displacement_index - 20)
    prior = bars[prior_start:displacement_index]
    prior_ranges = [item.range for item in prior if item.range > 0]
    prior_bodies = [item.body for item in prior if item.body > 0]
    med_range = median(prior_ranges) if prior_ranges else None
    med_body = median(prior_bodies) if prior_bodies else None

    previous_day = _previous_daily(days, raid_at)
    previous_session = _previous_session(sessions, raid_at)
    liq_class, liq_increments = _liquidity_class(
        swept_price=swept,
        raid_at=raid_at,
        side=side,
        previous_day=previous_day,
        previous_session=previous_session,
        m5_pivots=m5_pivots,
        m15_pivots=m15_pivots,
        tolerance=tolerance,
    )

    nearest_candidates = _candidate_liquidity_levels(
        entry_at=entry_at,
        entry=entry,
        side=side,
        previous_day=_previous_daily(days, entry_at),
        previous_session=_previous_session(sessions, entry_at),
        m5_pivots=m5_pivots,
        m15_pivots=m15_pivots,
    )
    nearest_price: Decimal | None = None
    nearest_type: str | None = None
    if nearest_candidates:
        nearest_price, nearest_type = nearest_candidates[0]

    protected = _protected_swing(
        m1_pivots,
        raid_at=raid_at,
        entry_at=entry_at,
        side=side,
        entry=entry,
    )

    session_start, session_end = _session_bounds(session, entry_at)
    elapsed = max(0, int((entry_at - session_start).total_seconds() // 60))
    remaining = max(0, int((session_end - entry_at).total_seconds() // 60))
    path_start = entry_index
    path_end = bisect.bisect_left(bar_times, session_end)
    path = bars[path_start:path_end]
    stop_index = _first_stop_index(path, side=side, stop=stop)
    nearest_index = (
        None
        if nearest_price is None
        else _first_touch_index(path, side=side, price=nearest_price)
    )
    two_r = entry + (Decimal("2") * risk if side is CapitalizerSide.LONG else -Decimal("2") * risk)
    two_r_index = _first_touch_index(path, side=side, price=two_r)
    macro_index = _first_touch_index(path, side=side, price=macro)

    far_edge = fvg_low if side is CapitalizerSide.LONG else fvg_high
    fvg_close_invalidated = False
    protected_touched: bool | None = None
    protected_close_invalidated: bool | None = None
    raid_close_invalidated = False
    if protected is not None:
        protected_touched = False
        protected_close_invalidated = False

    stop_bar: CapitalizerM1Bar | None = None
    for index, bar in enumerate(path):
        if stop_index is not None and index <= stop_index:
            if _close_invalidates(bar, side=side, level=far_edge):
                fvg_close_invalidated = True
            if protected is not None:
                assert protected_touched is not None
                assert protected_close_invalidated is not None
                if _bar_stop_touches(bar, side=side, stop=protected):
                    protected_touched = True
                if _close_invalidates(bar, side=side, level=protected):
                    protected_close_invalidated = True
        if _close_invalidates(bar, side=side, level=raid_extreme):
            raid_close_invalidated = True
        if stop_index is not None and index == stop_index:
            stop_bar = bar

    wick_only = False
    if stop_bar is not None:
        wick_only = not _close_invalidates(stop_bar, side=side, level=raid_extreme)

    raid_close_back = (
        raid_bar.close > swept
        if side is CapitalizerSide.LONG
        else raid_bar.close < swept
    )

    body_ratio = (
        Decimal("0")
        if displacement_bar.range <= 0
        else displacement_bar.body / displacement_bar.range
    )
    break_close_r = (
        max(Decimal("0"), displacement_bar.close - mss) / risk
        if side is CapitalizerSide.LONG
        else max(Decimal("0"), mss - displacement_bar.close) / risk
    )

    fvg_width = fvg_high - fvg_low
    if fvg_width <= 0:
        raise ValueError("FVG width must be positive")
    if side is CapitalizerSide.LONG:
        depth_fraction = (fvg_high - entry) / fvg_width
    else:
        depth_fraction = (entry - fvg_low) / fvg_width

    m15_pos = _range_position(
        m15_bars,
        m15_closes,
        entry_at,
        entry,
    )

    local = entry_at.astimezone(NEW_YORK)
    nearest_before = None if nearest_price is None else _before_stop(nearest_index, stop_index)
    nearest_after = None if nearest_price is None else _after_stop(nearest_index, stop_index)

    return TradeForensics(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        side=side.value,
        entry_at=entry_at.isoformat(),
        exit_at=str(raw["exit_at"]),
        original_exit_reason=str(raw["exit_reason"]),
        original_realized_r=str(raw["realized_gross_r"]),
        original_planned_reward_r=str(raw["planned_reward_r"]),
        entry_price=str(entry),
        original_stop_price=str(stop),
        original_macro_target_price=str(macro),
        ny_entry_hour=local.hour,
        ny_entry_minute=local.minute,
        session_elapsed_minutes=elapsed,
        session_remaining_minutes=remaining,
        htf_bias_age_minutes=int(raw["htf_bias_age_minutes"]),
        raid_at=raid_at.isoformat(),
        swept_pivot_price=str(swept),
        raid_extreme=str(raid_extreme),
        raid_depth_r=str(abs(raid_extreme - swept) / risk),
        raid_close_back_inside=raid_close_back,
        liquidity_level_class=liq_class,
        liquidity_level_distance_provider_increments=str(liq_increments),
        displacement_at=displacement_at.isoformat(),
        displacement_body_ratio=str(body_ratio),
        displacement_range_r=str(displacement_bar.range / risk),
        displacement_body_r=str(displacement_bar.body / risk),
        displacement_range_vs_prior20_median=(
            None if med_range is None or med_range <= 0 else str(displacement_bar.range / med_range)
        ),
        displacement_body_vs_prior20_median=(
            None if med_body is None or med_body <= 0 else str(displacement_bar.body / med_body)
        ),
        mss_level=str(mss),
        mss_break_close_r=str(break_close_r),
        mss_level_visible_m5=_matching_pivot(
            m5_pivots,
            moment=displacement_at,
            price=mss,
            kind="HIGH" if side is CapitalizerSide.LONG else "LOW",
            tolerance=tolerance,
        ),
        mss_level_visible_m15=_matching_pivot(
            m15_pivots,
            moment=displacement_at,
            price=mss,
            kind="HIGH" if side is CapitalizerSide.LONG else "LOW",
            tolerance=tolerance,
        ),
        fvg_low=str(fvg_low),
        fvg_high=str(fvg_high),
        fvg_width_r=str(fvg_width / risk),
        fvg_entry_depth_fraction=str(depth_fraction),
        fvg_far_edge=str(far_edge),
        m15_parent_state=_aligned_state(
            _structure_state(m15_bars, m15_pivots, entry_at),
            side,
        ),
        h1_parent_state=_aligned_state(
            _structure_state(h1_bars, h1_pivots, entry_at),
            side,
        ),
        h4_parent_state=_aligned_state(
            _structure_state(h4_bars, h4_pivots, entry_at),
            side,
        ),
        m15_range_position=None if m15_pos is None else str(m15_pos),
        protected_swing_price=None if protected is None else str(protected),
        protected_swing_distance_r=(
            None
            if protected is None
            else str(abs(entry - protected) / risk)
        ),
        nearest_causal_liquidity_price=(
            None if nearest_price is None else str(nearest_price)
        ),
        nearest_causal_liquidity_type=nearest_type,
        nearest_causal_liquidity_r=(
            None
            if nearest_price is None
            else str(abs(nearest_price - entry) / risk)
        ),
        two_r_price=str(two_r),
        nearest_liquidity_before_original_stop=nearest_before,
        two_r_before_original_stop=_before_stop(two_r_index, stop_index),
        macro_target_before_original_stop=_before_stop(macro_index, stop_index),
        nearest_liquidity_after_stop_before_session_end=nearest_after,
        two_r_after_stop_before_session_end=_after_stop(two_r_index, stop_index),
        macro_target_after_stop_before_session_end=_after_stop(macro_index, stop_index),
        original_stop_wick_only_reclaim=wick_only,
        raid_extreme_close_invalidated_before_session_end=raid_close_invalidated,
        fvg_far_edge_close_invalidated_before_original_stop=fvg_close_invalidated,
        protected_swing_touched_before_original_stop=protected_touched,
        protected_swing_close_invalidated_before_original_stop=protected_close_invalidated,
    )


def build_market(
    scanner_root: Path,
    m1_root: Path,
) -> tuple[MarketForensicsReport, tuple[TradeForensics, ...]]:
    source = _load_source_trades(scanner_root)
    symbol = str(source[0]["symbol"])
    session = str(source[0]["session"])
    if any(str(row["symbol"]) != symbol or str(row["session"]) != session for row in source):
        raise ValueError("market forensics source must contain one symbol/session")

    bars = _load_m1(m1_root)
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("market forensics M1 symbol mismatch")
    bar_times = tuple(bar.opened_at for bar in bars)

    m5_bars = _aggregate(bars, minutes=5)
    m15_bars = _aggregate(bars, minutes=15)
    h1_bars = _aggregate_higher(bars, hours=1)
    h4_bars = _aggregate_higher(bars, hours=4)
    m1_pivots = _m1_pivots(bars)
    m5_pivots = _pivots(m5_bars)
    m15_pivots = _pivots(m15_bars)
    h1_pivots = _pivots(h1_bars)
    h4_pivots = _pivots(h4_bars)
    m15_closes = tuple(item.closed_at for item in m15_bars)
    sessions = _session_extremes(bars)
    days = _daily_extremes(bars)

    enriched = tuple(
        _enrich_trade(
            row,
            bars=bars,
            bar_times=bar_times,
            m1_pivots=m1_pivots,
            m5_pivots=m5_pivots,
            m15_bars=m15_bars,
            m15_closes=m15_closes,
            m15_pivots=m15_pivots,
            h1_bars=h1_bars,
            h1_pivots=h1_pivots,
            h4_bars=h4_bars,
            h4_pivots=h4_pivots,
            sessions=sessions,
            days=days,
        )
        for row in source
    )

    stops = [row for row in enriched if row.original_exit_reason == "STOP"]
    report = MarketForensicsReport(
        identity=IDENTITY,
        source_identity=SCANNER_IDENTITY,
        symbol=symbol,
        session=session,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        source_trades=len(enriched),
        source_stops=len(stops),
        source_targets=sum(row.original_exit_reason == "TARGET" for row in enriched),
        source_session_exits=sum(
            row.original_exit_reason == "SESSION_EXIT" for row in enriched
        ),
        stop_trades_nearest_liquidity_before_stop=sum(
            row.nearest_liquidity_before_original_stop is True for row in stops
        ),
        stop_trades_two_r_before_stop=sum(row.two_r_before_original_stop for row in stops),
        stop_trades_wick_only_reclaim=sum(row.original_stop_wick_only_reclaim for row in stops),
        stop_trades_fvg_close_invalidated_before_stop=sum(
            row.fvg_far_edge_close_invalidated_before_original_stop for row in stops
        ),
        stop_trades_protected_swing_survived_stop=sum(
            row.protected_swing_close_invalidated_before_original_stop is False
            for row in stops
            if row.protected_swing_close_invalidated_before_original_stop is not None
        ),
        stop_trades_macro_target_after_stop_same_session=sum(
            row.macro_target_after_stop_before_session_end for row in stops
        ),
        liquidity_class_cohorts=_cohorts(
            enriched,
            selector=lambda row: row.liquidity_level_class,
        ),
        ny_hour_cohorts=_cohorts(
            enriched,
            selector=lambda row: f"NY_HOUR_{row.ny_entry_hour:02d}",
        ),
        planned_rr_cohorts=_cohorts(
            enriched,
            selector=lambda row: _rr_bin(Decimal(row.original_planned_reward_r)),
        ),
        bias_age_cohorts=_cohorts(
            enriched,
            selector=lambda row: _bias_age_bin(row.htf_bias_age_minutes),
        ),
        displacement_body_cohorts=_cohorts(
            enriched,
            selector=lambda row: _body_bin(Decimal(row.displacement_body_ratio)),
        ),
        displacement_relative_range_cohorts=_cohorts(
            enriched,
            selector=lambda row: _relative_bin(
                None
                if row.displacement_range_vs_prior20_median is None
                else Decimal(row.displacement_range_vs_prior20_median)
            ),
        ),
        m15_parent_cohorts=_cohorts(
            enriched,
            selector=lambda row: row.m15_parent_state,
        ),
    )
    return report, enriched


def write_market(
    report: MarketForensicsReport,
    rows: tuple[TradeForensics, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-stop-loss-root-forensics-1y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-ledger.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_market_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-stop-loss-root-forensics-1y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"root-forensics matrix requires 9 reports, got {len(paths)}")
    result: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("identity") != IDENTITY:
            raise ValueError("unexpected root-forensics market identity")
        result.append(dict(raw))
    if {str(item["symbol"]) for item in result} != EXPECTED_SYMBOLS:
        raise ValueError("root-forensics universe mismatch")
    return sorted(result, key=lambda item: str(item["symbol"]))


def _load_ledgers(root: Path) -> tuple[TradeForensics, ...]:
    rows: list[TradeForensics] = []
    for path in sorted(root.rglob("capitalizer-*-stop-loss-root-forensics-1y-v1-ledger.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    raw: Any = json.loads(line)
                    if not isinstance(raw, dict):
                        raise ValueError("root-forensics ledger row must be object")
                    rows.append(TradeForensics(**raw))
    return tuple(sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol)))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_market_reports(root)
    rows = _load_ledgers(root)
    stops = [row for row in rows if row.original_exit_reason == "STOP"]

    return {
        "identity": MATRIX_IDENTITY,
        "source_identity": SCANNER_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "source_trades": len(rows),
        "source_stops": len(stops),
        "source_targets": sum(row.original_exit_reason == "TARGET" for row in rows),
        "source_session_exits": sum(
            row.original_exit_reason == "SESSION_EXIT" for row in rows
        ),
        "stop_trades_nearest_liquidity_before_stop": sum(
            row.nearest_liquidity_before_original_stop is True for row in stops
        ),
        "stop_trades_two_r_before_stop": sum(
            row.two_r_before_original_stop for row in stops
        ),
        "stop_trades_wick_only_reclaim": sum(
            row.original_stop_wick_only_reclaim for row in stops
        ),
        "stop_trades_fvg_close_invalidated_before_stop": sum(
            row.fvg_far_edge_close_invalidated_before_original_stop for row in stops
        ),
        "stop_trades_protected_swing_survived_stop": sum(
            row.protected_swing_close_invalidated_before_original_stop is False
            for row in stops
            if row.protected_swing_close_invalidated_before_original_stop is not None
        ),
        "stop_trades_macro_target_after_stop_same_session": sum(
            row.macro_target_after_stop_before_session_end for row in stops
        ),
        "liquidity_class_cohorts": [
            asdict(item)
            for item in _cohorts(rows, selector=lambda row: row.liquidity_level_class)
        ],
        "ny_hour_cohorts": [
            asdict(item)
            for item in _cohorts(
                rows,
                selector=lambda row: f"NY_HOUR_{row.ny_entry_hour:02d}",
            )
        ],
        "planned_rr_cohorts": [
            asdict(item)
            for item in _cohorts(
                rows,
                selector=lambda row: _rr_bin(Decimal(row.original_planned_reward_r)),
            )
        ],
        "bias_age_cohorts": [
            asdict(item)
            for item in _cohorts(
                rows,
                selector=lambda row: _bias_age_bin(row.htf_bias_age_minutes),
            )
        ],
        "displacement_body_cohorts": [
            asdict(item)
            for item in _cohorts(
                rows,
                selector=lambda row: _body_bin(Decimal(row.displacement_body_ratio)),
            )
        ],
        "displacement_relative_range_cohorts": [
            asdict(item)
            for item in _cohorts(
                rows,
                selector=lambda row: _relative_bin(
                    None
                    if row.displacement_range_vs_prior20_median is None
                    else Decimal(row.displacement_range_vs_prior20_median)
                ),
            )
        ],
        "m15_parent_cohorts": [
            asdict(item)
            for item in _cohorts(rows, selector=lambda row: row.m15_parent_state)
        ],
        "markets": reports,
        "methodology_changed": False,
        "entries_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "filters_applied": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-stop-loss-root-forensics-1y-matrix-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("scanner_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows = build_market(args.scanner_root, args.m1_root)
        write_market(report, rows, args.output)
        print(
            json.dumps(
                {
                    "symbol": report.symbol,
                    "trades": report.source_trades,
                    "stops": report.source_stops,
                    "nearest_before_stop": report.stop_trades_nearest_liquidity_before_stop,
                    "two_r_before_stop": report.stop_trades_two_r_before_stop,
                    "wick_only_stop": report.stop_trades_wick_only_reclaim,
                    "fvg_invalidated_before_stop": (
                        report.stop_trades_fvg_close_invalidated_before_stop
                    ),
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
