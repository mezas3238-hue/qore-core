"""ICT 2022 source-faithful M1 entry replay for QORE Capitalizer — 1Y research window.

Research question:
Does the ICT 2022 execution route improve Capitalizer economics when only the entry
mechanic is changed?

Frozen comparison controls:
- higher-level source candidate remains the retained Capitalizer candidate;
- only directional liquidity-raid rejection candidates are admitted:
  LONG -> LOW_RAID_REJECTION
  SHORT -> HIGH_RAID_REJECTION;
- source stop remains unchanged (SOURCE_M5_DIRECTIONAL_EXTREME);
- source target remains unchanged (NEAREST_CAUSAL_TARGET_V2);
- same-session lifecycle remains unchanged;
- same-minute ambiguity remains STOP_FIRST / fail-closed.

ICT M1 execution route:
  directional liquidity raid already confirmed by the retained higher-level signal
  -> significant M1 displacement
  -> M1 market-structure shift through the latest confirmed short-term pivot
  -> directional M1 fair value gap created by that displacement
  -> first causal retracement into the FVG after FVG confirmation
  -> entry.

Order Block is deliberately NOT required in this laboratory.

Window:
  [2025-09-17, 2026-09-17)

This is consumed historical research, not a fresh holdout, economic candidate,
certification, live authorization or real-capital authorization.
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
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at

IDENTITY = "QORE_CAPITALIZER_ICT_2022_M1_ENTRY_1Y_REPLAY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_ICT_2022_M1_ENTRY_1Y_MATRIX_V1"
ENTRY_IDENTITY = "ICT_2022_RAID_MSS_DISPLACEMENT_FVG_FIRST_RETRACE"
WINDOW_START = datetime.fromisoformat("2025-09-17T00:00:00+00:00")
WINDOW_END = datetime.fromisoformat("2026-09-17T00:00:00+00:00")
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
class ICTM1Setup:
    displacement_index: int
    fvg_confirm_index: int
    mss_level: Decimal
    fvg_low: Decimal
    fvg_high: Decimal
    pivot_index: int


@dataclass(frozen=True, slots=True)
class ICTM1Trade:
    symbol: str
    session: str
    side: str
    higher_setup_signal_at: str
    source_event_labels: tuple[str, ...]
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
    m1_displacement_at: str
    m1_fvg_confirmed_at: str
    same_minute_stop_target_ambiguity: bool
    entry_definition: str = ENTRY_IDENTITY
    liquidity_raid_source: str = "RETAINED_HIGHER_LEVEL_DIRECTIONAL_RAID_REJECTION"
    displacement_required: bool = True
    m1_mss_required: bool = True
    m1_fvg_required: bool = True
    m1_order_block_required: bool = False
    stop_definition: str = "UNCHANGED_SOURCE_M5_DIRECTIONAL_EXTREME"
    target_definition: str = "UNCHANGED_NEAREST_CAUSAL_TARGET_V2"
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class ICTReplayMetrics:
    trades: int
    wins: int
    losses: int
    flats: int
    total_r: str
    mean_r: str | None
    gross_profit_r: str
    gross_loss_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    stop_exits: int
    target_exits: int
    session_exits: int
    ambiguous_stop_first_exits: int


@dataclass(frozen=True, slots=True)
class ICTMarketReport:
    identity: str
    entry_identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    source_candidates_in_window: int
    directional_raid_candidates: int
    non_raid_candidates_rejected: int
    ict_m1_entries: int
    ict_entry_rate_vs_raid_candidates: str
    metrics: ICTReplayMetrics | None
    rejection_reasons: tuple[tuple[str, int], ...]
    sessions_with_entry: int
    sessions_over_max3: int
    max_entries_one_session: int
    methodology_probe_only: bool = True
    entry_changed: bool = True
    higher_level_setup_changed: bool = False
    stop_changed: bool = False
    target_changed: bool = False
    lifecycle_changed: bool = False
    m1_order_block_required: bool = False
    synthetic_m1_used: bool = False
    interpolated_m1_used: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _aware(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return result


def _load_candidates(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"ICT replay requires one source candidate ledger, got {len(paths)}")
    result: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("source candidate must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("ICT replay rejects outcome-selected source candidates")
            signal = _aware(str(raw["signal_at"]))
            if WINDOW_START <= signal < WINDOW_END:
                result.append(raw)
    if not result:
        raise ValueError("ICT 1Y source window is empty")
    return tuple(result)


def _expected_raid(side: CapitalizerSide) -> str:
    return "LOW_RAID_REJECTION" if side is CapitalizerSide.LONG else "HIGH_RAID_REJECTION"


def _is_directional_raid(row: dict[str, Any]) -> bool:
    side = CapitalizerSide(str(row["side"]))
    labels = row.get("event_labels")
    if not isinstance(labels, list):
        raise ValueError("source event_labels must be list")
    return _expected_raid(side) in {str(label) for label in labels}


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
) -> ICTM1Setup | None:
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
    pivot_index = pivot_indices[-1]
    pivot = bars[pivot_index]
    mss_level = pivot.high if side is CapitalizerSide.LONG else pivot.low
    if side is CapitalizerSide.LONG:
        if displacement.close <= mss_level:
            return None
    elif displacement.close >= mss_level:
        return None

    first = bars[displacement_index - 1]
    third = bars[displacement_index + 1]
    if side is CapitalizerSide.LONG:
        if first.high >= third.low:
            return None
        fvg_low, fvg_high = first.high, third.low
    else:
        if first.low <= third.high:
            return None
        fvg_low, fvg_high = third.high, first.low

    return ICTM1Setup(
        displacement_index=displacement_index,
        fvg_confirm_index=displacement_index + 1,
        mss_level=mss_level,
        fvg_low=fvg_low,
        fvg_high=fvg_high,
        pivot_index=pivot_index,
    )


def _target_touched(
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


def _fvg_fill_price(
    bar: CapitalizerM1Bar,
    *,
    setup: ICTM1Setup,
    side: CapitalizerSide,
) -> Decimal | None:
    low = setup.fvg_low
    high = setup.fvg_high
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
    stop: Decimal,
) -> tuple[ICTM1Setup, int, Decimal, str] | tuple[None, None, None, str]:
    start_index = next(
        (index for index, bar in enumerate(bars) if bar.opened_at >= signal_at),
        None,
    )
    if start_index is None:
        return None, None, None, "NO_M1_AFTER_LIQUIDITY_RAID"

    saw_displacement = False
    saw_mss = False
    saw_fvg = False
    for displacement_index in range(max(2, start_index), len(bars) - 1):
        displacement = bars[displacement_index]
        if not _significant_displacement(displacement, side=side):
            continue
        saw_displacement = True

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
        fvg_exists = (
            first.high < third.low
            if side is CapitalizerSide.LONG
            else first.low > third.high
        )
        if not fvg_exists:
            continue
        saw_fvg = True

        setup = _candidate_setup(
            bars,
            displacement_index=displacement_index,
            side=side,
        )
        if setup is None:
            continue

        retest_start = setup.fvg_confirm_index + 1
        if _target_touched(
            bars,
            start_index=start_index,
            end_index=retest_start,
            side=side,
            target=target,
        ):
            return None, None, None, "TARGET_CONSUMED_BEFORE_ICT_RETRACE"

        for entry_index in range(retest_start, len(bars)):
            if _target_touched(
                bars,
                start_index=retest_start,
                end_index=entry_index,
                side=side,
                target=target,
            ):
                return None, None, None, "TARGET_CONSUMED_BEFORE_ICT_RETRACE"
            fill = _fvg_fill_price(
                bars[entry_index],
                setup=setup,
                side=side,
            )
            if fill is None:
                continue
            valid_geometry = (
                stop < fill < target
                if side is CapitalizerSide.LONG
                else target < fill < stop
            )
            if not valid_geometry:
                return None, None, None, "ICT_ENTRY_STOP_TARGET_GEOMETRY_INVALID"
            return setup, entry_index, fill, "ICT_M1_ENTRY_CONFIRMED"

    if not saw_displacement:
        reason = "M1_SIGNIFICANT_DISPLACEMENT_NOT_CONFIRMED"
    elif not saw_mss:
        reason = "M1_MSS_NOT_CONFIRMED"
    elif not saw_fvg:
        reason = "M1_FVG_NOT_CONFIRMED"
    else:
        reason = "M1_FVG_RETRACE_NOT_OBSERVED"
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
        raise ValueError("ICT lifecycle requires positive risk")
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
            if stop_hit:
                return Decimal("-1"), "STOP", held, target_hit, bar.closed_at
            continue
        if stop_hit:
            ambiguity = target_hit
            return Decimal("-1"), "STOP", held, ambiguity, bar.closed_at
        if target_hit:
            return (
                abs(target_price - entry_price) / risk,
                "TARGET",
                held,
                False,
                bar.closed_at,
            )
    delta = (
        last_close - entry_price
        if side is CapitalizerSide.LONG
        else entry_price - last_close
    )
    return delta / risk, "SESSION_EXIT", held, ambiguity, bars[-1].closed_at


def _metrics(trades: tuple[ICTM1Trade, ...]) -> ICTReplayMetrics | None:
    if not trades:
        return None
    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    values = tuple(Decimal(item.realized_gross_r) for item in ordered)
    gross_profit = sum((v for v in values if v > 0), Decimal("0"))
    gross_loss = -sum((v for v in values if v < 0), Decimal("0"))
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
        wins=sum(v > 0 for v in values),
        losses=sum(v < 0 for v in values),
        flats=sum(v == 0 for v in values),
        total_r=str(total),
        mean_r=str(total / Decimal(len(values))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=None if gross_loss == 0 else str(gross_profit / gross_loss),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=sum(t.exit_reason == "STOP" for t in ordered),
        target_exits=sum(t.exit_reason == "TARGET" for t in ordered),
        session_exits=sum(t.exit_reason == "SESSION_EXIT" for t in ordered),
        ambiguous_stop_first_exits=sum(
            t.same_minute_stop_target_ambiguity for t in ordered
        ),
    )


def _process_session(
    bars: tuple[CapitalizerM1Bar, ...],
    candidates: tuple[dict[str, Any], ...],
    *,
    session: CapitalizerSession,
    rejection: Counter[str],
) -> tuple[ICTM1Trade, ...]:
    result: list[ICTM1Trade] = []
    for row in candidates:
        side = CapitalizerSide(str(row["side"]))
        signal_at = _aware(str(row["signal_at"]))
        target = Decimal(str(row["target_price"]))
        stop = Decimal(str(row["stop_price"]))
        setup, entry_index, entry_price, reason = _find_entry(
            bars,
            signal_at=signal_at,
            side=side,
            target=target,
            stop=stop,
        )
        if setup is None or entry_index is None or entry_price is None:
            rejection[reason] += 1
            continue
        realized, exit_reason, held, ambiguous, exit_at = _lifecycle(
            bars,
            entry_index=entry_index,
            side=side,
            entry_price=entry_price,
            stop_price=stop,
            target_price=target,
        )
        risk = abs(entry_price - stop)
        labels_raw = row.get("event_labels")
        if not isinstance(labels_raw, list):
            raise ValueError("event_labels must be list")
        result.append(
            ICTM1Trade(
                symbol=str(row["symbol"]),
                session=session.value,
                side=side.value,
                higher_setup_signal_at=signal_at.isoformat(),
                source_event_labels=tuple(sorted(str(x) for x in labels_raw)),
                entry_at=bars[entry_index].opened_at.isoformat(),
                exit_at=exit_at.isoformat(),
                entry_price=str(entry_price),
                stop_price=str(stop),
                target_price=str(target),
                planned_reward_r=str(abs(target - entry_price) / risk),
                realized_gross_r=str(realized),
                exit_reason=exit_reason,
                m1_bars_held=held,
                m1_mss_level=str(setup.mss_level),
                m1_fvg_low=str(setup.fvg_low),
                m1_fvg_high=str(setup.fvg_high),
                m1_displacement_at=bars[setup.displacement_index].closed_at.isoformat(),
                m1_fvg_confirmed_at=bars[setup.fvg_confirm_index].closed_at.isoformat(),
                same_minute_stop_target_ambiguity=ambiguous,
            )
        )
    return tuple(result)


def build_market_report(
    candidate_root: Path,
    m1_root: Path,
) -> tuple[ICTMarketReport, tuple[ICTM1Trade, ...]]:
    all_candidates = _load_candidates(candidate_root)
    symbols = {str(row["symbol"]) for row in all_candidates}
    sessions = {str(row["session"]) for row in all_candidates}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("ICT market replay requires one symbol/session")
    symbol = next(iter(symbols))
    session = CapitalizerSession(next(iter(sessions)))

    raid_candidates = tuple(row for row in all_candidates if _is_directional_raid(row))
    if not raid_candidates:
        raise ValueError("ICT market replay has no directional raid candidates")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raid_candidates:
        signal = _aware(str(row["signal_at"]))
        grouped[_operating_date(signal, session)].append(row)

    rejection: Counter[str] = Counter()
    trades: list[ICTM1Trade] = []
    session_counts: Counter[str] = Counter()
    buffer: list[CapitalizerM1Bar] = []
    active_key: str | None = None
    processed_keys: set[str] = set()

    def flush() -> None:
        nonlocal buffer, active_key
        if active_key is None or not buffer:
            buffer = []
            return
        session_candidates = tuple(grouped.get(active_key, ()))
        if session_candidates:
            produced = _process_session(
                tuple(buffer),
                session_candidates,
                session=session,
                rejection=rejection,
            )
            trades.extend(produced)
            session_counts[active_key] = len(produced)
            processed_keys.add(active_key)
        buffer = []

    for bar in iter_cibo_m1(m1_root):
        if bar.symbol != symbol:
            raise ValueError("native M1 clone symbol mismatch")
        if not (WINDOW_START - timedelta(days=1) <= bar.opened_at < WINDOW_END + timedelta(days=1)):
            continue
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

    missing_keys = set(grouped) - processed_keys
    for key in missing_keys:
        rejection["M1_SESSION_EVIDENCE_UNAVAILABLE"] += len(grouped[key])

    ordered = tuple(sorted(trades, key=lambda item: (_aware(item.entry_at), item.symbol)))
    report = ICTMarketReport(
        identity=IDENTITY,
        entry_identity=ENTRY_IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        source_candidates_in_window=len(all_candidates),
        directional_raid_candidates=len(raid_candidates),
        non_raid_candidates_rejected=len(all_candidates) - len(raid_candidates),
        ict_m1_entries=len(ordered),
        ict_entry_rate_vs_raid_candidates=str(
            Decimal(len(ordered)) / Decimal(len(raid_candidates))
        ),
        metrics=_metrics(ordered),
        rejection_reasons=tuple(
            sorted(rejection.items(), key=lambda item: (-item[1], item[0]))
        ),
        sessions_with_entry=sum(count > 0 for count in session_counts.values()),
        sessions_over_max3=sum(
            count > MAX_EXECUTIONS_PER_SESSION for count in session_counts.values()
        ),
        max_entries_one_session=max(session_counts.values(), default=0),
    )
    return report, ordered


def write_market(
    report: ICTMarketReport,
    trades: tuple[ICTM1Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-ict-2022-m1-entry-1y-replay-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-ict-2022-m1-entry-1y-replay-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"ICT 1Y matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if {str(report["symbol"]) for report in reports} != EXPECTED_SYMBOLS:
        raise ValueError("ICT 1Y universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def _load_all_trades(root: Path) -> tuple[ICTM1Trade, ...]:
    result: list[ICTM1Trade] = []
    for path in sorted(root.rglob("capitalizer-*-ict-2022-m1-entry-1y-replay-v1-trades.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    raw = json.loads(line)
                    raw["source_event_labels"] = tuple(raw["source_event_labels"])
                    result.append(ICTM1Trade(**raw))
    return tuple(sorted(result, key=lambda item: (_aware(item.entry_at), item.symbol)))


def _apply_max3(trades: tuple[ICTM1Trade, ...]) -> tuple[ICTM1Trade, ...]:
    grouped: dict[str, list[ICTM1Trade]] = defaultdict(list)
    for trade in trades:
        session = CapitalizerSession(trade.session)
        key = f"{trade.session}:{_operating_date(_aware(trade.entry_at), session)}"
        grouped[key].append(trade)
    selected: list[ICTM1Trade] = []
    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=lambda item: (_aware(item.entry_at), item.symbol))
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol)))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    all_trades = _load_all_trades(root)
    max3 = _apply_max3(all_trades)
    gross_profit = Decimal("0")
    gross_loss = Decimal("0")
    total = Decimal("0")
    for report in reports:
        metrics = report.get("metrics")
        if isinstance(metrics, dict):
            gross_profit += Decimal(str(metrics["gross_profit_r"]))
            gross_loss += Decimal(str(metrics["gross_loss_r"]))
            total += Decimal(str(metrics["total_r"]))
    return {
        "identity": MATRIX_IDENTITY,
        "entry_identity": ENTRY_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "source_candidates_in_window": sum(
            int(report["source_candidates_in_window"]) for report in reports
        ),
        "directional_raid_candidates": sum(
            int(report["directional_raid_candidates"]) for report in reports
        ),
        "non_raid_candidates_rejected": sum(
            int(report["non_raid_candidates_rejected"]) for report in reports
        ),
        "ict_m1_entries": sum(int(report["ict_m1_entries"]) for report in reports),
        "aggregate_profit_factor": (
            None if gross_loss == 0 else str(gross_profit / gross_loss)
        ),
        "total_r": str(total),
        "max3_selected_trades": len(max3),
        "max3_metrics": None if (metrics := _metrics(max3)) is None else asdict(metrics),
        "markets": reports,
        "entry_changed": True,
        "higher_level_setup_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "lifecycle_changed": False,
        "m1_order_block_required": False,
        "quantile_or_stop_intelligence_used": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-ict-2022-m1-entry-1y-matrix-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
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
                    "symbol": report.symbol,
                    "raid_candidates": report.directional_raid_candidates,
                    "entries": report.ict_m1_entries,
                    "pf": None if report.metrics is None else report.metrics.profit_factor,
                    "total_r": None if report.metrics is None else report.metrics.total_r,
                    "dd": None if report.metrics is None else report.metrics.max_drawdown_r,
                    "ls": None if report.metrics is None else report.metrics.max_losing_streak,
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
