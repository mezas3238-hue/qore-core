"""Fixed-selection 1R repricing of the broad native-M1 Capitalizer ledger.

The source ledger is the immutable 10Y native-M1 replay that already required:
higher-level setup -> native M1 MSS -> native M1 FVG -> validated M1 Order Block
-> first causal OB retest.

This laboratory does not rescan admission and cannot add entries. It preserves the
exact source entries, stops, session assignment, M1 structure and portfolio MAX3
ordering. Only the exit target is repriced to 1.00R to test whether the current
MAX_RECOVERY target discovery generalizes to the much denser legacy M1 population.

Consumed laboratory evidence only. This module is not the source-faithful FTM
route, does not claim a fresh holdout, and cannot promote a rule automatically.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_native_m1_entry_replay_v1 as native,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)

IDENTITY = "QORE_CAPITALIZER_NATIVE_M1_FIXED_SELECTION_TARGET1_10Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_NATIVE_M1_FIXED_SELECTION_TARGET1_10Y_V1"
)
TARGET_R = Decimal("1.00")
SOURCE_RUN_ID = 35548099334
SOURCE_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
EXPECTED_RAW_TRADES = 21696
EXPECTED_SOURCE_MAX3_TRADES = 16600


@dataclass(frozen=True, slots=True)
class NativeM1Target1Outcome:
    symbol: str
    session: str
    side: str
    higher_setup_signal_at: str
    entry_at: str
    entry_price: str
    stop_price: str
    original_target_price: str
    original_planned_reward_r: str
    target_r: str
    target_price: str
    exit_at: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    same_minute_stop_target_ambiguity: bool
    m1_mss_level: str
    m1_fvg_low: str
    m1_fvg_high: str
    m1_order_block_low: str
    m1_order_block_high: str
    m1_displacement_at: str
    m1_fvg_confirmed_at: str


def _load_source_trades(root: Path) -> tuple[native.CapitalizerM1ReplayTrade, ...]:
    paths = sorted(root.rglob("capitalizer-*-native-m1-entry-replay-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(
            f"target1 native-M1 market requires one source ledger, got {len(paths)}"
        )
    rows: list[native.CapitalizerM1ReplayTrade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            trade = native.CapitalizerM1ReplayTrade(**json.loads(line))
            if trade.outcome_used_for_selection:
                raise ValueError("target1 native-M1 cannot consume outcome-selected trade")
            rows.append(trade)
    if not rows:
        raise ValueError("target1 native-M1 requires source trades")
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _metrics(trades: tuple[NativeM1Target1Outcome, ...]) -> dict[str, Any]:
    if not trades:
        raise ValueError("target1 native-M1 metrics require trades")
    ordered = tuple(
        sorted(
            trades,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )
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

    return {
        "trades": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / Decimal(len(values))),
        "gross_profit_r": str(gross_profit),
        "gross_loss_r": str(gross_loss),
        "profit_factor": (
            None if gross_loss == 0 else str(gross_profit / gross_loss)
        ),
        "max_drawdown_r": str(max_dd),
        "max_losing_streak": max_streak,
        "stop_exits": sum(item.exit_reason == "STOP" for item in ordered),
        "target_exits": sum(item.exit_reason == "TARGET" for item in ordered),
        "session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in ordered
        ),
        "ambiguous_stop_first_exits": sum(
            item.same_minute_stop_target_ambiguity for item in ordered
        ),
    }


def _simulate(
    trade: native.CapitalizerM1ReplayTrade,
    execution: tuple[CapitalizerM1Bar, ...],
) -> NativeM1Target1Outcome:
    entry_at = datetime.fromisoformat(trade.entry_at)
    entry_index = next(
        (
            index
            for index, bar in enumerate(execution)
            if bar.opened_at == entry_at
        ),
        None,
    )
    if entry_index is None:
        raise ValueError("target1 native-M1 entry timestamp missing from source M1")

    entry = Decimal(trade.entry_price)
    stop = Decimal(trade.stop_price)
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("target1 native-M1 requires positive source risk")
    side = CapitalizerSide(trade.side)
    target = (
        entry + TARGET_R * risk
        if side is CapitalizerSide.LONG
        else entry - TARGET_R * risk
    )
    realized, reason, held, ambiguous, exit_at = native._lifecycle(
        execution,
        entry_index=entry_index,
        side=side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
    )
    return NativeM1Target1Outcome(
        symbol=trade.symbol,
        session=trade.session,
        side=trade.side,
        higher_setup_signal_at=trade.higher_setup_signal_at,
        entry_at=trade.entry_at,
        entry_price=trade.entry_price,
        stop_price=trade.stop_price,
        original_target_price=trade.target_price,
        original_planned_reward_r=trade.planned_reward_r,
        target_r=str(TARGET_R),
        target_price=str(target),
        exit_at=exit_at.isoformat(),
        realized_gross_r=str(realized),
        exit_reason=reason,
        m1_bars_held=held,
        same_minute_stop_target_ambiguity=ambiguous,
        m1_mss_level=trade.m1_mss_level,
        m1_fvg_low=trade.m1_fvg_low,
        m1_fvg_high=trade.m1_fvg_high,
        m1_order_block_low=trade.m1_order_block_low,
        m1_order_block_high=trade.m1_order_block_high,
        m1_displacement_at=trade.m1_displacement_at,
        m1_fvg_confirmed_at=trade.m1_fvg_confirmed_at,
    )


def _source_execution_by_day(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
) -> dict[str, tuple[CapitalizerM1Bar, ...]]:
    grouped: dict[str, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        if capitalizer_session_at(bar.opened_at) is not session:
            continue
        key = native._operating_date(bar.opened_at, session)
        grouped[key].append(bar)
    return {
        key: tuple(sorted(rows, key=lambda item: item.opened_at))
        for key, rows in grouped.items()
    }


def build_market_report(
    replay_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[NativeM1Target1Outcome, ...]]:
    source = _load_source_trades(replay_root)
    symbols = {item.symbol for item in source}
    sessions = {item.session for item in source}
    if len(symbols) != 1 or sessions != {session.value}:
        raise ValueError("target1 native-M1 source market/session mismatch")
    symbol = next(iter(symbols))

    bars = tuple(iter_cibo_m1(m1_root))
    if not bars or any(bar.symbol != symbol for bar in bars):
        raise ValueError("target1 native-M1 source bars mismatch")
    execution_by_day = _source_execution_by_day(bars, session=session)

    outcomes: list[NativeM1Target1Outcome] = []
    for trade in source:
        operating_day = native._operating_date(
            datetime.fromisoformat(trade.entry_at),
            session,
        )
        execution = execution_by_day.get(operating_day, ())
        if not execution:
            raise ValueError("target1 native-M1 missing source execution session")
        outcomes.append(_simulate(trade, execution))

    ordered = tuple(
        sorted(
            outcomes,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "target_r": str(TARGET_R),
        "source_run_id": SOURCE_RUN_ID,
        "source_sha": SOURCE_SHA,
        "fixed_source_entries": len(source),
        "repriced_entries": len(ordered),
        "metrics": _metrics(ordered),
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "m1_structure_changed": False,
        "only_target_r_changed": True,
        "new_entries_allowed": False,
        "entry_timeframe": "M1_NATIVE",
        "m1_mss_required": True,
        "m1_fvg_required": True,
        "m1_order_block_required": True,
        "development_window_role": "CONSUMED_10Y_LABORATORY",
        "fresh_holdout_claimed": False,
        "outcome_used_for_admission": False,
        "automatic_promotion_allowed": False,
        "source_faithful_ftm_route_claimed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, ordered


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-native-m1-fixed-selection-target1-10y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(
            f"target1 native-M1 matrix requires 9 reports, got {len(paths)}"
        )
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_outcomes(root: Path) -> tuple[NativeM1Target1Outcome, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-native-m1-fixed-selection-target1-10y-v1-outcomes.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"target1 native-M1 matrix requires 9 ledgers, got {len(paths)}"
        )
    rows: list[NativeM1Target1Outcome] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(NativeM1Target1Outcome(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _apply_max3(
    trades: tuple[NativeM1Target1Outcome, ...],
) -> tuple[tuple[NativeM1Target1Outcome, ...], int]:
    grouped: dict[str, list[NativeM1Target1Outcome]] = defaultdict(list)
    for trade in trades:
        session = CapitalizerSession(trade.session)
        moment = datetime.fromisoformat(trade.entry_at)
        key = f"{trade.session}:{native._operating_date(moment, session)}"
        grouped[key].append(trade)

    selected: list[NativeM1Target1Outcome] = []
    unresolved = 0
    for key in sorted(grouped):
        by_time: dict[str, list[NativeM1Target1Outcome]] = defaultdict(list)
        for trade in grouped[key]:
            by_time[trade.entry_at].append(trade)
        slots = MAX_EXECUTIONS_PER_SESSION
        for entry_at in sorted(by_time):
            if slots <= 0:
                break
            tied = sorted(by_time[entry_at], key=lambda item: item.symbol)
            if len(tied) > slots:
                unresolved += len(tied)
                continue
            selected.extend(tied)
            slots -= len(tied)
    return (
        tuple(
            sorted(
                selected,
                key=lambda item: (
                    datetime.fromisoformat(item.entry_at),
                    item.symbol,
                ),
            )
        ),
        unresolved,
    )


def _year_rows(
    trades: tuple[NativeM1Target1Outcome, ...],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[NativeM1Target1Outcome]] = defaultdict(list)
    for trade in trades:
        year = str(
            datetime.fromisoformat(trade.entry_at).astimezone(native.NEW_YORK).year
        )
        grouped[year].append(trade)
    return [
        {
            "year": year,
            "trades": len(grouped[year]),
            "metrics": _metrics(tuple(grouped[year])),
        }
        for year in sorted(grouped)
    ]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    outcomes = _load_outcomes(root)
    if len(outcomes) != EXPECTED_RAW_TRADES:
        raise ValueError("target1 native-M1 raw source count mismatch")
    selected, unresolved = _apply_max3(outcomes)
    if len(selected) != EXPECTED_SOURCE_MAX3_TRADES:
        raise ValueError("target1 native-M1 MAX3 selection count mismatch")

    by_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        subset = tuple(item for item in selected if item.session == session.value)
        by_session[session.value] = {
            "trades": len(subset),
            "metrics": _metrics(subset),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": len(reports),
        "target_r": str(TARGET_R),
        "raw_trades": len(outcomes),
        "max3_trades": len(selected),
        "max3_metrics": _metrics(selected),
        "by_session": by_session,
        "by_year": _year_rows(selected),
        "same_timestamp_competition_rejected": unresolved,
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "m1_structure_changed": False,
        "only_target_r_changed": True,
        "new_entries_allowed": False,
        "entry_timeframe": "M1_NATIVE",
        "m1_mss_required": True,
        "m1_fvg_required": True,
        "m1_order_block_required": True,
        "development_window_role": "CONSUMED_10Y_LABORATORY",
        "fresh_holdout_claimed": False,
        "outcome_used_for_admission": False,
        "automatic_promotion_allowed": False,
        "source_faithful_ftm_route_claimed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_market(
    report: dict[str, Any],
    outcomes: tuple[NativeM1Target1Outcome, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-native-m1-fixed-selection-target1-10y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-outcomes.jsonl").open("w", encoding="utf-8") as handle:
        for outcome in outcomes:
            handle.write(json.dumps(asdict(outcome), sort_keys=True) + "\n")


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-native-m1-fixed-selection-target1-10y-v1.json"
    )
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
        report, outcomes = build_market_report(
            args.replay_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, outcomes, args.output)
        print(
            json.dumps(
                {
                    "identity": report["identity"],
                    "symbol": report["symbol"],
                    "repriced_entries": report["repriced_entries"],
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
