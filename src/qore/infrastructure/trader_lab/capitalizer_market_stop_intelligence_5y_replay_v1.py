"""Five-year economic replay for QORE Capitalizer Market Stop Cognition.

This replay changes only the initial stop geometry on already-accepted native-M1 entries.

Frozen route:
    higher-level setup -> M1 MSS -> M1 FVG -> validated M1 Order Block -> same entry
    -> Market Stop Cognition structural invalidation -> same structural target

Current executable research subset:
- Structural Brain only.
- The native-M1 protected swing equals the validated Order Block directional extreme under
  the frozen entry contract.
- Execution buffer is exactly zero because temporal stability did not support freezing an
  adaptive market-memory buffer yet.
- QORE Risk sizing is not simulated and remains sovereign.
- Same-minute target is never credited optimistically; stop remains fail-closed.

The source 2021-09-17..2026-09-17 window is already consumed evidence. This run is a
research replay, not a fresh holdout and not certification.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

IDENTITY = "QORE_CAPITALIZER_MARKET_STOP_INTELLIGENCE_5Y_REPLAY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STOP_INTELLIGENCE_5Y_MATRIX_V1"
SOURCE_REPLAY_IDENTITY = "QORE_CAPITALIZER_NATIVE_M1_ENTRY_REPLAY_V1"
STOP_ENGINE_IDENTITY = "QORE_CAPITALIZER_MARKET_STOP_COGNITIVE_ENGINE_V1"
EXPECTED_M1_IDENTITY = "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1"
EXPECTED_M1_SCHEMA = "qore.capitalizer.cibo.raw_m1.v1"
PRICE_SCALE = Decimal(100_000)
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class M1Bar:
    symbol: str
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    @property
    def closed_at(self) -> datetime:
        return self.opened_at + timedelta(minutes=1)


@dataclass(slots=True)
class _ReplayState:
    row_index: int
    entry_at: datetime
    session_end: datetime
    side: str
    entry: Decimal
    stop: Decimal
    target: Decimal
    held: int = 0
    last_close: Decimal | None = None
    realized_r: Decimal | None = None
    exit_reason: str | None = None
    exit_at: datetime | None = None
    ambiguity: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerStopReplayMetrics:
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


@dataclass(frozen=True, slots=True)
class CapitalizerStopIntelligence5YMarketReport:
    identity: str
    stop_engine_identity: str
    symbol: str
    session: str
    source_trade_count: int
    structural_executed_trades: int
    stop_geometry_rejected: int
    baseline_all_metrics: CapitalizerStopReplayMetrics
    baseline_matched_metrics: CapitalizerStopReplayMetrics
    structural_metrics: CapitalizerStopReplayMetrics
    median_structural_stop_width_vs_baseline: str
    structural_stop_narrower: int
    structural_stop_wider: int
    structural_stop_equal: int
    transition_counts: tuple[tuple[str, int], ...]
    profit_factor_delta: str | None
    drawdown_reduction_r: str
    losing_streak_reduction: int
    structural_dd_le_6r: bool
    source_window: str = "2021-09-17_TO_2026-09-17"
    entry_changed: bool = False
    target_changed: bool = False
    methodology_changed: bool = False
    structural_anchor: str = "M1_PROTECTED_SWING_EQUALS_VALIDATED_OB_EXTREME"
    execution_buffer_ticks: str = "0"
    adaptive_buffer_frozen: bool = False
    qore_risk_sizing_simulated: bool = False
    spread_slippage_latency_applied: bool = False
    evidence_status: str = "CONSUMED_5Y_RESEARCH_REPLAY"
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stop replay timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _session_bounds(moment: datetime, session: str) -> tuple[datetime, datetime]:
    local = moment.astimezone(NEW_YORK)
    date = local.date()
    if session == "ASIA":
        if local.timetz().replace(tzinfo=None) < time(2, 0):
            start_date = date - timedelta(days=1)
            end_date = date
        else:
            start_date = date
            end_date = date + timedelta(days=1)
        start = datetime.combine(start_date, time(20, 0), tzinfo=NEW_YORK)
        end = datetime.combine(end_date, time(2, 0), tzinfo=NEW_YORK)
    elif session == "LONDON":
        start = datetime.combine(date, time(2, 0), tzinfo=NEW_YORK)
        end = datetime.combine(date, time(8, 30), tzinfo=NEW_YORK)
    elif session == "NEW_YORK":
        start = datetime.combine(date, time(8, 30), tzinfo=NEW_YORK)
        end = datetime.combine(date, time(16, 0), tzinfo=NEW_YORK)
    else:
        raise ValueError(f"unsupported Capitalizer session: {session}")
    return start.astimezone(UTC), end.astimezone(UTC)


def _price(row: dict[str, Any], field: str, *, digits: int) -> Decimal:
    value = row.get(field)
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be positive provider-relative int")
    return (Decimal(value) / PRICE_SCALE).quantize(Decimal(1).scaleb(-digits))


def _bar(row: dict[str, Any]) -> M1Bar:
    if row.get("schema") != EXPECTED_M1_SCHEMA:
        raise ValueError("unexpected native-M1 schema")
    if row.get("identity") != EXPECTED_M1_IDENTITY:
        raise ValueError("unexpected native-M1 identity")
    symbol = row.get("canonical_symbol")
    opened = row.get("opened_at")
    digits = row.get("digits")
    if not isinstance(symbol, str) or not isinstance(opened, str) or type(digits) is not int:
        raise ValueError("invalid native-M1 row")
    return M1Bar(
        symbol=symbol,
        opened_at=_aware(opened),
        open=_price(row, "open_relative", digits=digits),
        high=_price(row, "high_relative", digits=digits),
        low=_price(row, "low_relative", digits=digits),
        close=_price(row, "close_relative", digits=digits),
    )


def _utc_minute(moment: datetime) -> int:
    return int(moment.timestamp()) // 60


def _row_utc_minute(line: str) -> int:
    marker = '"utc_timestamp_in_minutes": '
    start = line.find(marker)
    if start < 0:
        raise ValueError("native-M1 row missing utc_timestamp_in_minutes")
    start += len(marker)
    comma = line.find(",", start)
    brace = line.find("}", start)
    ends = [position for position in (comma, brace) if position >= 0]
    if not ends:
        raise ValueError("invalid utc_timestamp_in_minutes")
    return int(line[start:min(ends)])


def _iter_relevant_m1(
    root: Path,
    session_intervals: list[tuple[datetime, datetime]],
) -> Iterable[tuple[M1Bar, bool]]:
    intervals = sorted(
        (_utc_minute(start), _utc_minute(end))
        for start, end in set(session_intervals)
    )
    if not intervals:
        raise ValueError("stop replay requires trade session intervals")
    ledger = root / "RAW_M1_LEDGER"
    paths = sorted(ledger.glob("*.jsonl"))
    if not paths:
        raise ValueError("RAW_M1_LEDGER partitions not found")

    interval_index = 0
    last_emitted_interval: int | None = None
    previous: datetime | None = None
    previous_symbol: str | None = None
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                minute = _row_utc_minute(line)
                while interval_index < len(intervals) and minute >= intervals[interval_index][1]:
                    interval_index += 1
                if interval_index >= len(intervals):
                    return
                start_minute, end_minute = intervals[interval_index]
                if minute < start_minute or minute >= end_minute:
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("native-M1 row must be object")
                current = _bar(raw)
                if _utc_minute(current.opened_at) != minute:
                    raise ValueError("native-M1 minute key mismatch")
                if previous is not None and current.opened_at <= previous:
                    raise ValueError("native-M1 chronology must increase")
                if previous_symbol is not None and current.symbol != previous_symbol:
                    raise ValueError("one M1 root must contain one symbol")
                new_interval = last_emitted_interval != interval_index
                previous = current.opened_at
                previous_symbol = current.symbol
                last_emitted_interval = interval_index
                yield current, new_interval


def _one_path(root: Path, pattern: str) -> Path:
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected exactly one {pattern}, got {len(paths)}")
    return paths[0]


def _load_replay(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = json.loads(
        _one_path(root, "capitalizer-*-native-m1-entry-replay-v1.json").read_text(
            encoding="utf-8"
        )
    )
    if summary.get("identity") != SOURCE_REPLAY_IDENTITY:
        raise ValueError("unexpected native-M1 source replay identity")
    if summary.get("entry_timeframe") != "M1_NATIVE":
        raise ValueError("stop replay requires native-M1 entries")
    if summary.get("methodology_changed") is not False:
        raise ValueError("stop replay requires unchanged methodology")

    trades: list[dict[str, Any]] = []
    path = _one_path(root, "capitalizer-*-native-m1-entry-replay-v1-trades.jsonl")
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("source trade must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("stop replay rejects outcome-selected trades")
            trades.append(raw)
    if len(trades) != int(summary.get("m1_entries", -1)):
        raise ValueError("source replay summary/trade count mismatch")
    if not trades:
        raise ValueError("stop replay requires trades")
    return summary, trades


def structural_stop_for_row(row: dict[str, Any]) -> Decimal | None:
    side = str(row["side"])
    entry = Decimal(str(row["entry_price"]))
    target = Decimal(str(row["target_price"]))
    if side == "LONG":
        stop = Decimal(str(row["m1_order_block_low"]))
        return stop if stop < entry < target else None
    if side == "SHORT":
        stop = Decimal(str(row["m1_order_block_high"]))
        return stop if target < entry < stop else None
    raise ValueError(f"unsupported side: {side}")


def _metrics(rows: list[dict[str, Any]], value_key: str) -> CapitalizerStopReplayMetrics:
    if not rows:
        return CapitalizerStopReplayMetrics(
            trades=0,
            wins=0,
            losses=0,
            flats=0,
            total_r="0",
            mean_r=None,
            gross_profit_r="0",
            gross_loss_r="0",
            profit_factor=None,
            max_drawdown_r="0",
            max_losing_streak=0,
            stop_exits=0,
            target_exits=0,
            session_exits=0,
        )
    ordered = sorted(rows, key=lambda item: _aware(str(item["entry_at"])))
    values = [Decimal(str(item[value_key])) for item in ordered]
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
    exit_key = "exit_reason" if value_key == "realized_gross_r" else "structural_exit_reason"
    return CapitalizerStopReplayMetrics(
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
        stop_exits=sum(str(row[exit_key]) == "STOP" for row in rows),
        target_exits=sum(str(row[exit_key]) == "TARGET" for row in rows),
        session_exits=sum(str(row[exit_key]) == "SESSION_EXIT" for row in rows),
    )


def _finalize_session_exit(state: _ReplayState, when: datetime) -> None:
    if state.realized_r is not None:
        return
    last_close = state.entry if state.last_close is None else state.last_close
    delta = (
        last_close - state.entry
        if state.side == "LONG"
        else state.entry - last_close
    )
    risk = abs(state.entry - state.stop)
    state.realized_r = delta / risk
    state.exit_reason = "SESSION_EXIT"
    state.exit_at = when


def _replay_structural(rows: list[dict[str, Any]], m1_root: Path) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    states: list[_ReplayState] = []
    starts: dict[datetime, list[int]] = defaultdict(list)
    intervals: list[tuple[datetime, datetime]] = []

    for source in rows:
        stop = structural_stop_for_row(source)
        if stop is None:
            continue
        row = dict(source)
        entry_at = _aware(str(row["entry_at"]))
        _, session_end = _session_bounds(entry_at, str(row["session"]))
        entry = Decimal(str(row["entry_price"]))
        target = Decimal(str(row["target_price"]))
        baseline_stop = Decimal(str(row["stop_price"]))
        baseline_risk = abs(entry - baseline_stop)
        structural_risk = abs(entry - stop)
        if baseline_risk <= 0 or structural_risk <= 0:
            raise ValueError("stop replay requires positive risk")
        row["baseline_stop_price"] = str(baseline_stop)
        row["structural_stop_price"] = str(stop)
        row["structural_stop_width_vs_baseline"] = str(structural_risk / baseline_risk)
        row["structural_planned_reward_r"] = str(abs(target - entry) / structural_risk)
        row["execution_buffer_ticks"] = "0"
        row["stop_engine_identity"] = STOP_ENGINE_IDENTITY
        row["structural_anchor"] = "M1_PROTECTED_SWING_EQUALS_VALIDATED_OB_EXTREME"
        row["outcome_used_for_selection"] = False
        accepted_index = len(accepted)
        accepted.append(row)
        state = _ReplayState(
            row_index=accepted_index,
            entry_at=entry_at,
            session_end=session_end,
            side=str(row["side"]),
            entry=entry,
            stop=stop,
            target=target,
        )
        state_index = len(states)
        states.append(state)
        starts[entry_at].append(state_index)
        intervals.append(_session_bounds(entry_at, str(row["session"])))

    if not accepted:
        raise ValueError("no trades have valid structural stop geometry")

    active: set[int] = set()
    last_bar_close: datetime | None = None
    for bar, new_interval in _iter_relevant_m1(m1_root, intervals):
        if new_interval and active:
            for state_index in tuple(active):
                _finalize_session_exit(states[state_index], last_bar_close or bar.opened_at)
            active.clear()

        for state_index in starts.get(bar.opened_at, ()):
            active.add(state_index)

        completed: list[int] = []
        for state_index in tuple(active):
            state = states[state_index]
            state.held += 1
            state.last_close = bar.close
            stop_hit = bar.low <= state.stop if state.side == "LONG" else bar.high >= state.stop
            target_hit = (
                bar.high >= state.target
                if state.side == "LONG"
                else bar.low <= state.target
            )
            risk = abs(state.entry - state.stop)
            if state.held == 1:
                if stop_hit:
                    state.realized_r = Decimal("-1")
                    state.exit_reason = "STOP"
                    state.exit_at = bar.closed_at
                    state.ambiguity = target_hit
                    completed.append(state_index)
            elif stop_hit:
                state.realized_r = Decimal("-1")
                state.exit_reason = "STOP"
                state.exit_at = bar.closed_at
                state.ambiguity = target_hit
                completed.append(state_index)
            elif target_hit:
                state.realized_r = abs(state.target - state.entry) / risk
                state.exit_reason = "TARGET"
                state.exit_at = bar.closed_at
                completed.append(state_index)

            if state_index not in completed and bar.closed_at >= state.session_end:
                _finalize_session_exit(state, bar.closed_at)
                completed.append(state_index)

        for state_index in completed:
            active.discard(state_index)
        last_bar_close = bar.closed_at

    if active:
        if last_bar_close is None:
            raise ValueError("no native-M1 bars reached accepted trades")
        for state_index in tuple(active):
            _finalize_session_exit(states[state_index], last_bar_close)

    for state in states:
        if state.realized_r is None or state.exit_reason is None or state.exit_at is None:
            raise ValueError("structural replay left unresolved trade")
        row = accepted[state.row_index]
        row["structural_realized_gross_r"] = str(state.realized_r)
        row["structural_exit_reason"] = state.exit_reason
        row["structural_exit_at"] = state.exit_at.isoformat()
        row["structural_m1_bars_held"] = state.held
        row["structural_same_minute_stop_target_ambiguity"] = state.ambiguity
    return accepted


def build_market_report(
    replay_root: Path,
    m1_root: Path,
) -> tuple[CapitalizerStopIntelligence5YMarketReport, list[dict[str, Any]]]:
    summary, source_rows = _load_replay(replay_root)
    structural_rows = _replay_structural(source_rows, m1_root)
    matched_source = {
        str(row["higher_setup_signal_at"])
        for row in structural_rows
    }
    baseline_matched = [
        row for row in source_rows
        if str(row["higher_setup_signal_at"]) in matched_source
    ]
    baseline_all_metrics = _metrics(source_rows, "realized_gross_r")
    baseline_matched_metrics = _metrics(baseline_matched, "realized_gross_r")
    structural_metrics = _metrics(structural_rows, "structural_realized_gross_r")

    ratios = [
        Decimal(str(row["structural_stop_width_vs_baseline"]))
        for row in structural_rows
    ]
    transitions = Counter(
        (str(row["exit_reason"]), str(row["structural_exit_reason"]))
        for row in structural_rows
    )
    baseline_pf = baseline_matched_metrics.profit_factor
    structural_pf = structural_metrics.profit_factor
    pf_delta = (
        None
        if baseline_pf is None or structural_pf is None
        else str(Decimal(structural_pf) - Decimal(baseline_pf))
    )
    dd_reduction = (
        Decimal(baseline_matched_metrics.max_drawdown_r)
        - Decimal(structural_metrics.max_drawdown_r)
    )
    return (
        CapitalizerStopIntelligence5YMarketReport(
            identity=IDENTITY,
            stop_engine_identity=STOP_ENGINE_IDENTITY,
            symbol=str(summary["symbol"]),
            session=str(summary["session"]),
            source_trade_count=len(source_rows),
            structural_executed_trades=len(structural_rows),
            stop_geometry_rejected=len(source_rows) - len(structural_rows),
            baseline_all_metrics=baseline_all_metrics,
            baseline_matched_metrics=baseline_matched_metrics,
            structural_metrics=structural_metrics,
            median_structural_stop_width_vs_baseline=str(median(ratios)),
            structural_stop_narrower=sum(value < 1 for value in ratios),
            structural_stop_wider=sum(value > 1 for value in ratios),
            structural_stop_equal=sum(value == 1 for value in ratios),
            transition_counts=tuple(
                (f"{before}->{after}", count)
                for (before, after), count in sorted(transitions.items())
            ),
            profit_factor_delta=pf_delta,
            drawdown_reduction_r=str(dd_reduction),
            losing_streak_reduction=(
                baseline_matched_metrics.max_losing_streak
                - structural_metrics.max_losing_streak
            ),
            structural_dd_le_6r=Decimal(structural_metrics.max_drawdown_r) <= Decimal("6"),
        ),
        structural_rows,
    )


def write_market(
    report: CapitalizerStopIntelligence5YMarketReport,
    rows: list[dict[str, Any]],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-stop-intelligence-5y-replay-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _load_market_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-stop-intelligence-5y-replay-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"nine-market matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    expected = {
        "AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD",
        "NAS100", "USDCAD", "USDJPY", "XAUUSD",
    }
    if {str(item["symbol"]) for item in reports} != expected:
        raise ValueError("stop-intelligence replay universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_market_reports(root)
    def metric(report: dict[str, Any], key: str, field: str) -> Decimal:
        return Decimal(str(report[key][field]))

    baseline_gp = sum(
        (metric(report, "baseline_matched_metrics", "gross_profit_r") for report in reports),
        Decimal("0"),
    )
    baseline_gl = sum(
        (metric(report, "baseline_matched_metrics", "gross_loss_r") for report in reports),
        Decimal("0"),
    )
    structural_gp = sum(
        (metric(report, "structural_metrics", "gross_profit_r") for report in reports),
        Decimal("0"),
    )
    structural_gl = sum(
        (metric(report, "structural_metrics", "gross_loss_r") for report in reports),
        Decimal("0"),
    )
    return {
        "identity": MATRIX_IDENTITY,
        "stop_engine_identity": STOP_ENGINE_IDENTITY,
        "market_count": 9,
        "source_window": "2021-09-17_TO_2026-09-17",
        "source_trade_count": sum(int(report["source_trade_count"]) for report in reports),
        "structural_executed_trades": sum(
            int(report["structural_executed_trades"]) for report in reports
        ),
        "stop_geometry_rejected": sum(
            int(report["stop_geometry_rejected"]) for report in reports
        ),
        "baseline_pooled_profit_factor": (
            None if baseline_gl == 0 else str(baseline_gp / baseline_gl)
        ),
        "structural_pooled_profit_factor": (
            None if structural_gl == 0 else str(structural_gp / structural_gl)
        ),
        "baseline_total_r": str(
            sum(
                (metric(report, "baseline_matched_metrics", "total_r") for report in reports),
                Decimal("0"),
            )
        ),
        "structural_total_r": str(
            sum(
                (metric(report, "structural_metrics", "total_r") for report in reports),
                Decimal("0"),
            )
        ),
        "markets_pf_improved": [
            report["symbol"]
            for report in reports
            if report["profit_factor_delta"] is not None
            and Decimal(str(report["profit_factor_delta"])) > 0
        ],
        "markets_dd_reduced": [
            report["symbol"]
            for report in reports
            if Decimal(str(report["drawdown_reduction_r"])) > 0
        ],
        "markets_losing_streak_reduced": [
            report["symbol"]
            for report in reports
            if int(report["losing_streak_reduction"]) > 0
        ],
        "markets_structural_dd_le_6r": [
            report["symbol"]
            for report in reports
            if bool(report["structural_dd_le_6r"])
        ],
        "markets": reports,
        "entry_changed": False,
        "target_changed": False,
        "methodology_changed": False,
        "execution_buffer_ticks": "0",
        "adaptive_buffer_frozen": False,
        "qore_risk_sizing_simulated": False,
        "spread_slippage_latency_applied": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-stop-intelligence-5y-matrix-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("replay_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        market_report, rows = build_market_report(args.replay_root, args.m1_root)
        write_market(market_report, rows, args.output)
        print(
            json.dumps(
                {
                    "identity": market_report.identity,
                    "symbol": market_report.symbol,
                    "trades": market_report.structural_executed_trades,
                    "baseline_pf": market_report.baseline_matched_metrics.profit_factor,
                    "structural_pf": market_report.structural_metrics.profit_factor,
                    "baseline_dd": market_report.baseline_matched_metrics.max_drawdown_r,
                    "structural_dd": market_report.structural_metrics.max_drawdown_r,
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
