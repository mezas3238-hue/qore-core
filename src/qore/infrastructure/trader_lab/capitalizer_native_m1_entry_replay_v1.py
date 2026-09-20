"""Native-M1 entry replay for QORE Capitalizer.

The higher-level Capitalizer methodology is unchanged. This replay consumes the exact
already-retained higher-level candidate ledger from the original three-session replay and
changes only the execution resolution:

    frozen higher-level setup -> native M1 MSS -> native M1 FVG
    -> native M1 validated Order Block -> first causal OB retest -> entry

The M1 Order Block uses the already-reviewed QORE/TTrades mechanic: the immediately
preceding consecutive opposing-candle series is validated by a directional close through
that series. The same displacement must also break confirmed short-term structure and
form the directional three-candle FVG. No M1 is synthesized from M5.

Target remains the exact target carried by the frozen higher-level candidate. Initial stop
is the structural extreme of the validated M1 opposing-candle series (the execution-layer
protected swing). Lifecycle remains same-session and fail-closed. Same-minute uncertainty
never receives optimistic target-first treatment.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    BAR_DURATION,
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)

IDENTITY = "QORE_CAPITALIZER_NATIVE_M1_ENTRY_REPLAY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_NATIVE_M1_ENTRY_REPLAY_V1"
NEW_YORK = ZoneInfo("America/New_York")
SOURCE_REPLAY_RUN_ID = 35528346941
SOURCE_REPLAY_SHA = "e0338846170003fd7b346c98883f63257b6cdf45"


@dataclass(frozen=True, slots=True)
class CapitalizerM1EntrySetup:
    displacement_index: int
    fvg_confirm_index: int
    mss_level: Decimal
    fvg_low: Decimal
    fvg_high: Decimal
    order_block_low: Decimal
    order_block_high: Decimal
    protected_swing: Decimal
    order_block_start_index: int
    order_block_end_index: int


@dataclass(frozen=True, slots=True)
class CapitalizerM1ReplayTrade:
    symbol: str
    session: str
    side: str
    higher_setup_signal_at: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    target_price: str
    planned_reward_r: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    m1_mss_level: str
    m1_fvg_low: str
    m1_fvg_high: str
    m1_order_block_low: str
    m1_order_block_high: str
    m1_displacement_at: str
    m1_fvg_confirmed_at: str
    m1_order_block_definition: str = "ttrades-opposing-series-confirmed-by-close"
    entry_definition: str = "FIRST_CAUSAL_M1_VALIDATED_OB_RETEST"
    stop_definition: str = "M1_VALIDATED_OB_STRUCTURAL_EXTREME_PROTECTED_SWING"
    target_definition: str = "UNCHANGED_HIGHER_LEVEL_TARGET"
    same_minute_stop_target_ambiguity: bool = False
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerNativeM1MarketReport:
    identity: str
    symbol: str
    session: str
    higher_level_candidates: int
    m1_entries: int
    m1_entry_rate: str
    metrics: CapitalizerR0Metrics | None
    rejection_reasons: tuple[tuple[str, int], ...]
    entries_by_year: tuple[tuple[str, int], ...]
    entries_per_year_median: str
    entries_per_year_mean: str
    sessions_with_entry: int
    sessions_over_max3: int
    max_entries_one_session: int
    methodology_changed: bool = False
    higher_level_setup_changed: bool = False
    session_contract_changed: bool = False
    target_contract_changed: bool = False
    entry_timeframe: str = "M1_NATIVE"
    m1_mss_required: bool = True
    m1_fvg_required: bool = True
    m1_order_block_required: bool = True
    synthetic_m1_used: bool = False
    interpolated_m1_used: bool = False
    outcome_aware_selection: bool = False
    fresh_holdout_claimed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerNativeM1Matrix:
    identity: str
    markets: tuple[CapitalizerNativeM1MarketReport, ...]
    total_higher_level_candidates: int
    total_m1_entries: int
    m1_entry_rate: str
    entries_by_session: tuple[tuple[str, int], ...]
    aggregate_pf: str | None
    total_gross_r: str
    methodology_changed: bool = False
    entry_timeframe: str = "M1_NATIVE"
    m1_mss_required: bool = True
    m1_fvg_required: bool = True
    m1_order_block_required: bool = True
    synthetic_m1_used: bool = False
    interpolated_m1_used: bool = False
    fresh_holdout_claimed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False


def _load_candidates(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"native M1 replay requires exactly one candidate ledger, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw: Any = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("candidate row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("higher-level candidate cannot be outcome-selected")
            rows.append(raw)
    if not rows:
        raise ValueError("native M1 replay requires higher-level candidates")
    return tuple(rows)


def _operating_date(moment: datetime, session: CapitalizerSession) -> str:
    local = moment.astimezone(NEW_YORK)
    if session is CapitalizerSession.ASIA and local.hour < 2:
        return (local.date() - timedelta(days=1)).isoformat()
    return local.date().isoformat()


def _pivot_indices(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    before_index: int,
    high: bool,
) -> tuple[int, ...]:
    result: list[int] = []
    for index in range(1, max(1, before_index)):
        if index + 1 >= len(bars) or index + 1 > before_index:
            break
        left = bars[index - 1]
        center = bars[index]
        right = bars[index + 1]
        if high and center.high > left.high and center.high > right.high:
            result.append(index)
        if not high and center.low < left.low and center.low < right.low:
            result.append(index)
    return tuple(result)


def _opposing_series(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    before_index: int,
    side: CapitalizerSide,
) -> tuple[int, ...]:
    selected: list[int] = []
    index = before_index - 1
    while index >= 0:
        bar = bars[index]
        opposing = (
            bar.close < bar.open
            if side is CapitalizerSide.LONG
            else bar.close > bar.open
        )
        if not opposing:
            break
        selected.append(index)
        index -= 1
    selected.reverse()
    return tuple(selected)


def _significant_displacement(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
) -> bool:
    if bar.range <= 0:
        return False
    directional = (
        bar.close > bar.open
        if side is CapitalizerSide.LONG
        else bar.close < bar.open
    )
    return directional and bar.body > (bar.range - bar.body)


def _candidate_setup(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    displacement_index: int,
    side: CapitalizerSide,
) -> CapitalizerM1EntrySetup | None:
    if displacement_index <= 1 or displacement_index + 1 >= len(bars):
        return None
    displacement = bars[displacement_index]
    if not _significant_displacement(displacement, side=side):
        return None

    pivot_indices = _pivot_indices(
        bars,
        before_index=displacement_index - 1,
        high=side is CapitalizerSide.LONG,
    )
    if not pivot_indices:
        return None
    pivot = bars[pivot_indices[-1]]
    mss_level = pivot.high if side is CapitalizerSide.LONG else pivot.low
    mss = (
        displacement.close > mss_level
        if side is CapitalizerSide.LONG
        else displacement.close < mss_level
    )
    if not mss:
        return None

    first = bars[displacement_index - 1]
    third = bars[displacement_index + 1]
    if side is CapitalizerSide.LONG:
        if not first.high < third.low:
            return None
        fvg_low, fvg_high = first.high, third.low
    else:
        if not first.low > third.high:
            return None
        fvg_low, fvg_high = third.high, first.low

    series_indices = _opposing_series(
        bars,
        before_index=displacement_index,
        side=side,
    )
    if not series_indices:
        return None
    series = tuple(bars[index] for index in series_indices)
    ob_confirmed = (
        displacement.close > max(bar.open for bar in series)
        if side is CapitalizerSide.LONG
        else displacement.close < min(bar.open for bar in series)
    )
    if not ob_confirmed:
        return None

    ob_low = min(bar.low for bar in series)
    ob_high = max(bar.high for bar in series)
    protected = ob_low if side is CapitalizerSide.LONG else ob_high
    return CapitalizerM1EntrySetup(
        displacement_index=displacement_index,
        fvg_confirm_index=displacement_index + 1,
        mss_level=mss_level,
        fvg_low=fvg_low,
        fvg_high=fvg_high,
        order_block_low=ob_low,
        order_block_high=ob_high,
        protected_swing=protected,
        order_block_start_index=series_indices[0],
        order_block_end_index=series_indices[-1],
    )


def _target_touched_before_entry(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    start_index: int,
    end_index: int,
    side: CapitalizerSide,
    target: Decimal,
) -> bool:
    for bar in bars[start_index:end_index]:
        if side is CapitalizerSide.LONG and bar.high >= target:
            return True
        if side is CapitalizerSide.SHORT and bar.low <= target:
            return True
    return False


def _fill_price(
    bar: CapitalizerM1Bar,
    *,
    setup: CapitalizerM1EntrySetup,
    side: CapitalizerSide,
) -> Decimal | None:
    low = setup.order_block_low
    high = setup.order_block_high
    if bar.high < low or bar.low > high:
        return None

    if low <= bar.open <= high:
        return bar.open
    if side is CapitalizerSide.LONG:
        if bar.open > high and bar.low <= high:
            return high
        return None
    if bar.open < low and bar.high >= low:
        return low
    return None


def _find_entry(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    signal_at: datetime,
    side: CapitalizerSide,
    target: Decimal,
) -> tuple[CapitalizerM1EntrySetup, int, Decimal, str] | tuple[None, None, None, str]:
    start_index = next(
        (index for index, bar in enumerate(bars) if bar.opened_at >= signal_at),
        None,
    )
    if start_index is None:
        return None, None, None, "NO_M1_AFTER_HIGHER_SETUP"

    saw_mss = False
    saw_fvg = False
    saw_ob = False
    for displacement_index in range(max(2, start_index), len(bars) - 1):
        displacement = bars[displacement_index]
        if not _significant_displacement(displacement, side=side):
            continue

        pivots = _pivot_indices(
            bars,
            before_index=displacement_index - 1,
            high=side is CapitalizerSide.LONG,
        )
        if not pivots:
            continue
        pivot = bars[pivots[-1]]
        mss_level = pivot.high if side is CapitalizerSide.LONG else pivot.low
        if side is CapitalizerSide.LONG:
            if displacement.close <= mss_level:
                continue
        elif displacement.close >= mss_level:
            continue
        saw_mss = True

        first = bars[displacement_index - 1]
        third = bars[displacement_index + 1]
        fvg = (
            first.high < third.low
            if side is CapitalizerSide.LONG
            else first.low > third.high
        )
        if not fvg:
            continue
        saw_fvg = True

        series_indices = _opposing_series(
            bars,
            before_index=displacement_index,
            side=side,
        )
        if not series_indices:
            continue
        series = tuple(bars[index] for index in series_indices)
        ob_confirmed = (
            displacement.close > max(bar.open for bar in series)
            if side is CapitalizerSide.LONG
            else displacement.close < min(bar.open for bar in series)
        )
        if not ob_confirmed:
            continue
        saw_ob = True

        setup = _candidate_setup(
            bars,
            displacement_index=displacement_index,
            side=side,
        )
        if setup is None:
            continue

        retest_start = setup.fvg_confirm_index + 1
        if _target_touched_before_entry(
            bars,
            start_index=start_index,
            end_index=retest_start,
            side=side,
            target=target,
        ):
            return None, None, None, "TARGET_CONSUMED_BEFORE_M1_ENTRY"

        for entry_index in range(retest_start, len(bars)):
            if _target_touched_before_entry(
                bars,
                start_index=retest_start,
                end_index=entry_index,
                side=side,
                target=target,
            ):
                return None, None, None, "TARGET_CONSUMED_BEFORE_M1_ENTRY"
            entry_price = _fill_price(
                bars[entry_index],
                setup=setup,
                side=side,
            )
            if entry_price is None:
                continue
            if side is CapitalizerSide.LONG:
                if not setup.protected_swing < entry_price < target:
                    continue
            else:
                if not target < entry_price < setup.protected_swing:
                    continue
            return setup, entry_index, entry_price, "M1_ENTRY_CONFIRMED"

    if not saw_mss:
        reason = "M1_MSS_NOT_CONFIRMED"
    elif not saw_fvg:
        reason = "M1_FVG_NOT_CONFIRMED"
    elif not saw_ob:
        reason = "M1_ORDER_BLOCK_NOT_CONFIRMED"
    else:
        reason = "M1_ORDER_BLOCK_RETEST_NOT_OBSERVED"
    return None, None, None, reason


def _lifecycle(
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
        raise ValueError("M1 lifecycle requires positive risk")

    last_close = entry_price
    held = 0
    ambiguity = False
    for index in range(entry_index, len(bars)):
        bar = bars[index]
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
            # Fill ordering inside the entry minute is unavailable. Never credit an
            # entry-minute target optimistically. A stop touch remains fail-closed.
            if stop_hit:
                return Decimal("-1"), "STOP", held, target_hit, bar.closed_at
            continue

        if stop_hit:
            ambiguity = target_hit
            return Decimal("-1"), "STOP", held, ambiguity, bar.closed_at
        if target_hit:
            reward = abs(target_price - entry_price)
            return reward / risk, "TARGET", held, False, bar.closed_at

    delta = (
        last_close - entry_price
        if side is CapitalizerSide.LONG
        else entry_price - last_close
    )
    return delta / risk, "SESSION_EXIT", held, ambiguity, bars[-1].closed_at


def _metrics(trades: tuple[CapitalizerM1ReplayTrade, ...]) -> CapitalizerR0Metrics | None:
    if not trades:
        return None
    values = tuple(Decimal(item.realized_gross_r) for item in trades)
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

    planned = tuple(Decimal(item.planned_reward_r) for item in trades)
    return CapitalizerR0Metrics(
        trades=len(trades),
        wins=sum(value > 0 for value in values),
        losses=sum(value < 0 for value in values),
        flats=sum(value == 0 for value in values),
        total_gross_r=str(total),
        mean_gross_r=str(total / Decimal(len(values))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=None if gross_loss == 0 else str(gross_profit / gross_loss),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        median_planned_reward_r=str(median(planned)),
        median_bars_held=str(median(item.m1_bars_held for item in trades)),
        stop_exits=sum(item.exit_reason == "STOP" for item in trades),
        target_exits=sum(item.exit_reason == "TARGET" for item in trades),
        session_exits=sum(item.exit_reason == "SESSION_EXIT" for item in trades),
        ambiguous_stop_first_exits=sum(
            item.same_minute_stop_target_ambiguity for item in trades
        ),
    )


def _process_session(
    bars: tuple[CapitalizerM1Bar, ...],
    candidates: tuple[dict[str, Any], ...],
    *,
    session: CapitalizerSession,
    rejection: Counter[str],
) -> tuple[CapitalizerM1ReplayTrade, ...]:
    result: list[CapitalizerM1ReplayTrade] = []
    for row in candidates:
        side = CapitalizerSide(str(row["side"]))
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        target = Decimal(str(row["target_price"]))
        setup, entry_index, entry_price, reason = _find_entry(
            bars,
            signal_at=signal_at,
            side=side,
            target=target,
        )
        if setup is None or entry_index is None or entry_price is None:
            rejection[reason] += 1
            continue

        stop = setup.protected_swing
        realized, exit_reason, held, ambiguous, exit_at = _lifecycle(
            bars,
            entry_index=entry_index,
            side=side,
            entry_price=entry_price,
            stop_price=stop,
            target_price=target,
        )
        risk = abs(entry_price - stop)
        reward = abs(target - entry_price)
        result.append(
            CapitalizerM1ReplayTrade(
                symbol=str(row["symbol"]),
                session=session.value,
                side=side.value,
                higher_setup_signal_at=signal_at.isoformat(),
                entry_at=bars[entry_index].opened_at.isoformat(),
                exit_at=exit_at.isoformat(),
                entry_price=str(entry_price),
                stop_price=str(stop),
                target_price=str(target),
                planned_reward_r=str(reward / risk),
                realized_gross_r=str(realized),
                exit_reason=exit_reason,
                m1_bars_held=held,
                m1_mss_level=str(setup.mss_level),
                m1_fvg_low=str(setup.fvg_low),
                m1_fvg_high=str(setup.fvg_high),
                m1_order_block_low=str(setup.order_block_low),
                m1_order_block_high=str(setup.order_block_high),
                m1_displacement_at=bars[setup.displacement_index].closed_at.isoformat(),
                m1_fvg_confirmed_at=bars[setup.fvg_confirm_index].closed_at.isoformat(),
                same_minute_stop_target_ambiguity=ambiguous,
            )
        )
    return tuple(result)


def build_market_report(
    *,
    candidate_root: Path,
    m1_root: Path,
) -> tuple[CapitalizerNativeM1MarketReport, tuple[CapitalizerM1ReplayTrade, ...]]:
    candidates = _load_candidates(candidate_root)
    symbols = {str(row["symbol"]) for row in candidates}
    sessions = {str(row["session"]) for row in candidates}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("native M1 replay requires one market/session")
    symbol = next(iter(symbols))
    session = CapitalizerSession(next(iter(sessions)))

    grouped_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        signal = datetime.fromisoformat(str(row["signal_at"]))
        grouped_candidates[_operating_date(signal, session)].append(row)

    rejection: Counter[str] = Counter()
    trades: list[CapitalizerM1ReplayTrade] = []
    session_counts: Counter[str] = Counter()
    buffer: list[CapitalizerM1Bar] = []
    active_key: str | None = None

    def flush() -> None:
        nonlocal buffer, active_key
        if active_key is None or not buffer:
            buffer = []
            return
        session_candidates = tuple(grouped_candidates.get(active_key, ()))
        if session_candidates:
            produced = _process_session(
                tuple(buffer),
                session_candidates,
                session=session,
                rejection=rejection,
            )
            trades.extend(produced)
            session_counts[active_key] += len(produced)
        buffer = []

    for bar in iter_cibo_m1(m1_root):
        if bar.symbol != symbol:
            raise ValueError("M1 clone symbol does not match higher-level candidates")
        if capitalizer_session_at(bar.opened_at) is not session:
            if buffer:
                flush()
                active_key = None
            continue
        key = _operating_date(bar.opened_at, session)
        if active_key is None:
            active_key = key
        elif key != active_key:
            flush()
            active_key = key
        buffer.append(bar)
    flush()

    missing_sessions = set(grouped_candidates) - set(session_counts)
    # session_counts has no key when candidates exist but no entries; those were processed
    # through flush and may remain zero. Distinguish unavailable M1 sessions by checking
    # rejection accounting against candidate count.
    accounted = len(trades) + sum(rejection.values())
    if accounted < len(candidates):
        rejection["M1_SESSION_EVIDENCE_UNAVAILABLE"] += len(candidates) - accounted

    ordered = tuple(
        sorted(
            trades,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )
    by_year: Counter[str] = Counter()
    for trade in ordered:
        by_year[str(datetime.fromisoformat(trade.entry_at).astimezone(NEW_YORK).year)] += 1
    years = tuple(str(year) for year in range(2016, 2027))
    year_counts = tuple((year, by_year[year]) for year in years)
    values = tuple(count for _, count in year_counts)
    over_max3 = sum(count > 3 for count in session_counts.values())
    report = CapitalizerNativeM1MarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        higher_level_candidates=len(candidates),
        m1_entries=len(ordered),
        m1_entry_rate=str(Decimal(len(ordered)) / Decimal(len(candidates))),
        metrics=_metrics(ordered),
        rejection_reasons=tuple(
            sorted(rejection.items(), key=lambda item: (-item[1], item[0]))
        ),
        entries_by_year=year_counts,
        entries_per_year_median=str(median(values)),
        entries_per_year_mean=str(Decimal(sum(values)) / Decimal(len(values))),
        sessions_with_entry=sum(count > 0 for count in session_counts.values()),
        sessions_over_max3=over_max3,
        max_entries_one_session=max(session_counts.values(), default=0),
    )
    del missing_sessions
    return report, ordered


def write_market(
    report: CapitalizerNativeM1MarketReport,
    trades: tuple[CapitalizerM1ReplayTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-native-m1-entry-replay-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> tuple[CapitalizerNativeM1MarketReport, ...]:
    paths = sorted(root.rglob("capitalizer-*-native-m1-entry-replay-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"native M1 matrix requires 9 reports, got {len(paths)}")
    reports: list[CapitalizerNativeM1MarketReport] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        metrics_raw = raw.get("metrics")
        reports.append(
            CapitalizerNativeM1MarketReport(
                **{
                    **raw,
                    "metrics": None if metrics_raw is None else CapitalizerR0Metrics(**metrics_raw),
                    "rejection_reasons": tuple(
                        (str(item[0]), int(item[1])) for item in raw["rejection_reasons"]
                    ),
                    "entries_by_year": tuple(
                        (str(item[0]), int(item[1])) for item in raw["entries_by_year"]
                    ),
                }
            )
        )
    return tuple(sorted(reports, key=lambda item: item.symbol))


def build_matrix(root: Path) -> CapitalizerNativeM1Matrix:
    reports = _load_reports(root)
    expected = {
        "AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD",
        "NAS100", "USDCAD", "USDJPY", "XAUUSD",
    }
    if {item.symbol for item in reports} != expected:
        raise ValueError("native M1 replay universe mismatch")

    total_candidates = sum(item.higher_level_candidates for item in reports)
    total_entries = sum(item.m1_entries for item in reports)
    session_counts: Counter[str] = Counter()
    gross_profit = Decimal("0")
    gross_loss = Decimal("0")
    total_r = Decimal("0")
    for report in reports:
        session_counts[report.session] += report.m1_entries
        if report.metrics is not None:
            gross_profit += Decimal(report.metrics.gross_profit_r)
            gross_loss += Decimal(report.metrics.gross_loss_r)
            total_r += Decimal(report.metrics.total_gross_r)
    return CapitalizerNativeM1Matrix(
        identity=MATRIX_IDENTITY,
        markets=reports,
        total_higher_level_candidates=total_candidates,
        total_m1_entries=total_entries,
        m1_entry_rate=str(Decimal(total_entries) / Decimal(total_candidates)),
        entries_by_session=tuple(sorted(session_counts.items())),
        aggregate_pf=None if gross_loss == 0 else str(gross_profit / gross_loss),
        total_gross_r=str(total_r),
    )


def write_matrix(report: CapitalizerNativeM1Matrix, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-native-m1-entry-replay-v1.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# QORE Capitalizer — Native M1 Entry Replay V1",
        "",
        "Methodology unchanged. Entry resolution only: M1 MSS + FVG + validated Order Block.",
        "",
        "| Market | Higher setups | M1 entries | Entry rate | PF | DD | LS |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for market in report.markets:
        metrics = market.metrics
        lines.append(
            f"| {market.symbol} | {market.higher_level_candidates} | {market.m1_entries} | "
            f"{Decimal(market.m1_entry_rate) * 100:.2f}% | "
            f"{'-' if metrics is None else metrics.profit_factor} | "
            f"{'-' if metrics is None else metrics.max_drawdown_r + 'R'} | "
            f"{'-' if metrics is None else metrics.max_losing_streak} |"
        )
    lines.extend(
        [
            "",
            f"- Total higher-level setups: {report.total_higher_level_candidates}",
            f"- Native M1 entries: {report.total_m1_entries}",
            f"- Native M1 entry rate: {Decimal(report.m1_entry_rate) * 100:.2f}%",
            f"- Aggregate PF (gross pooled): {report.aggregate_pf}",
            f"- Aggregate gross R: {report.total_gross_r}",
        ]
    )
    (output / "capitalizer-nine-market-native-m1-entry-replay-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("candidate_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, trades = build_market_report(
            candidate_root=args.candidate_root,
            m1_root=args.m1_root,
        )
        write_market(report, trades, args.output)
        print(
            json.dumps(
                {
                    "identity": report.identity,
                    "symbol": report.symbol,
                    "higher_level_candidates": report.higher_level_candidates,
                    "m1_entries": report.m1_entries,
                    "m1_entry_rate": report.m1_entry_rate,
                    "profit_factor": None if report.metrics is None else report.metrics.profit_factor,
                    "max_drawdown_r": None if report.metrics is None else report.metrics.max_drawdown_r,
                },
                sort_keys=True,
            )
        )
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "total_higher_level_candidates": report.total_higher_level_candidates,
                "total_m1_entries": report.total_m1_entries,
                "m1_entry_rate": report.m1_entry_rate,
                "aggregate_pf": report.aggregate_pf,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
