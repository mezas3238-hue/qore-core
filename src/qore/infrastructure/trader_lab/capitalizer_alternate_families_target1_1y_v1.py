"""Fixed-selection 1R census for two pre-existing Capitalizer families.

This laboratory reuses the exact entries and stops produced by the consumed
Fast-Fractal H1-M5-M1 and Scalping-Standard H1-M15-M1 1Y replays. It does not
re-run their admission logic and cannot add trades. Only the fixed reward target
is changed from 2R to 1R, matching the current MAX_RECOVERY target candidate.

Purpose: determine whether either already-existing family contains independent
economic edge worth carrying into later density research.

Consumed laboratory evidence only. No promotion, holdout, LIVE or capital
authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_fast_fractal_h1_m5_m1_1y_v1 as fast,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalping_standard_h1_m15_m1_1y_v1 as standard,
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
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    WINDOW_END,
    _lifecycle,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _index_day_inputs,
)

IDENTITY = "QORE_CAPITALIZER_ALTERNATE_FAMILIES_TARGET1_1Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_ALTERNATE_FAMILIES_TARGET1_1Y_V1"
TARGET_R = Decimal("1.00")
FAST_SOURCE_RUN_ID = 35861327955
FAST_SOURCE_SHA = "f70def28997d772939c9bc23c2333a077842f467"
STANDARD_SOURCE_RUN_ID = 35861313294
STANDARD_SOURCE_SHA = "dda2868d198d1021988c0be4b8d2cca404707525"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
EXPECTED_FAST_RAW = 327
EXPECTED_STANDARD_RAW = 191


@dataclass(frozen=True, slots=True)
class AlternateTargetOutcome:
    family: str
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    entry_price: str
    stop_price: str
    target_r: str
    target_price: str
    exit_at: str
    realized_gross_r: str
    exit_reason: str
    same_minute_stop_target_ambiguity: bool


def _load_fast(root: Path) -> tuple[fast.FastFractalTrade, ...]:
    trades = fast._load_trades(root)
    if not trades:
        raise ValueError("alternate-family census requires fast-fractal trades")
    return trades


def _load_standard(
    root: Path,
) -> tuple[standard.ScalpingStandardTrade, ...]:
    trades = standard._load_trades(root)
    if not trades:
        raise ValueError("alternate-family census requires scalping-standard trades")
    return trades


def _metrics(trades: tuple[AlternateTargetOutcome, ...]) -> dict[str, Any]:
    if not trades:
        raise ValueError("alternate-family metrics require trades")
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
    drawdown = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
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
        "max_drawdown_r": str(drawdown),
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
    *,
    family: str,
    trade: Any,
    execution: tuple[CapitalizerM1Bar, ...],
) -> AlternateTargetOutcome:
    entry_at = datetime.fromisoformat(str(trade.entry_at))
    entry_index = next(
        (
            index
            for index, bar in enumerate(execution)
            if bar.opened_at == entry_at
        ),
        None,
    )
    if entry_index is None:
        raise ValueError("alternate-family entry timestamp missing from native M1")

    entry = Decimal(str(trade.entry_price))
    stop = Decimal(str(trade.stop_price))
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("alternate-family trade requires positive risk")
    side = CapitalizerSide(str(trade.side))
    target = (
        entry + TARGET_R * risk
        if side is CapitalizerSide.LONG
        else entry - TARGET_R * risk
    )
    realized, reason, _, ambiguous, exit_at = _lifecycle(
        execution,
        entry_index=entry_index,
        side=side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
    )
    return AlternateTargetOutcome(
        family=family,
        symbol=str(trade.symbol),
        session=str(trade.session),
        operating_date=str(trade.operating_date),
        side=str(trade.side),
        entry_at=str(trade.entry_at),
        entry_price=str(entry),
        stop_price=str(stop),
        target_r=str(TARGET_R),
        target_price=str(target),
        exit_at=exit_at.isoformat(),
        realized_gross_r=str(realized),
        exit_reason=reason,
        same_minute_stop_target_ambiguity=ambiguous,
    )


def _run_family(
    *,
    family: str,
    trades: tuple[Any, ...],
    execution_by_day: dict[str, tuple[CapitalizerM1Bar, ...]],
) -> tuple[AlternateTargetOutcome, ...]:
    outcomes: list[AlternateTargetOutcome] = []
    for trade in trades:
        execution = execution_by_day.get(str(trade.operating_date), ())
        if not execution:
            raise ValueError("alternate-family trade missing operating session")
        outcomes.append(
            _simulate(
                family=family,
                trade=trade,
                execution=execution,
            )
        )
    return tuple(
        sorted(
            outcomes,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def build_market_report(
    fast_root: Path,
    standard_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[
    dict[str, Any],
    tuple[AlternateTargetOutcome, ...],
]:
    fast_trades = _load_fast(fast_root)
    standard_trades = _load_standard(standard_root)

    symbols = {trade.symbol for trade in fast_trades} | {
        trade.symbol for trade in standard_trades
    }
    if len(symbols) != 1:
        raise ValueError("alternate-family market inputs must contain one symbol")
    symbol = next(iter(symbols))
    if any(trade.session != session.value for trade in fast_trades):
        raise ValueError("fast-fractal session mismatch")
    if any(trade.session != session.value for trade in standard_trades):
        raise ValueError("scalping-standard session mismatch")

    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if fast.LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not bars or any(bar.symbol != symbol for bar in bars):
        raise ValueError("alternate-family native M1 symbol mismatch")
    execution_by_day, _ = _index_day_inputs(bars, session=session)

    fast_outcomes = _run_family(
        family="FAST_FRACTAL_H1_M5_M1",
        trades=fast_trades,
        execution_by_day=execution_by_day,
    )
    standard_outcomes = _run_family(
        family="SCALPING_STANDARD_H1_M15_M1",
        trades=standard_trades,
        execution_by_day=execution_by_day,
    )
    all_outcomes = tuple(
        sorted(
            (*fast_outcomes, *standard_outcomes),
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.family,
            ),
        )
    )

    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "target_r": str(TARGET_R),
        "fast_source_run_id": FAST_SOURCE_RUN_ID,
        "fast_source_sha": FAST_SOURCE_SHA,
        "standard_source_run_id": STANDARD_SOURCE_RUN_ID,
        "standard_source_sha": STANDARD_SOURCE_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "fast_fixed_entries": len(fast_outcomes),
        "standard_fixed_entries": len(standard_outcomes),
        "fast_target1_metrics": _metrics(fast_outcomes),
        "standard_target1_metrics": _metrics(standard_outcomes),
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "only_target_r_changed": True,
        "new_entries_allowed": False,
        "development_window_role": "CONSUMED_LABORATORY",
        "fresh_holdout_claimed": False,
        "outcome_used_for_admission": False,
        "automatic_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, all_outcomes


def _max3(
    trades: tuple[AlternateTargetOutcome, ...],
) -> tuple[AlternateTargetOutcome, ...]:
    grouped: dict[str, list[AlternateTargetOutcome]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)
    selected: list[AlternateTargetOutcome] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-alternate-families-target1-1y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(
            f"alternate-family matrix requires 9 reports, got {len(paths)}"
        )
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_outcomes(root: Path) -> tuple[AlternateTargetOutcome, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-alternate-families-target1-1y-v1-outcomes.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"alternate-family matrix requires 9 ledgers, got {len(paths)}"
        )
    result: list[AlternateTargetOutcome] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    result.append(
                        AlternateTargetOutcome(**json.loads(line))
                    )
    return tuple(result)


def _entry_key(
    trade: AlternateTargetOutcome,
) -> tuple[str, str, str, str]:
    return (
        trade.symbol,
        trade.session,
        trade.operating_date,
        trade.entry_at,
    )


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    outcomes = _load_outcomes(root)
    fast_raw = tuple(
        item for item in outcomes if item.family == "FAST_FRACTAL_H1_M5_M1"
    )
    standard_raw = tuple(
        item
        for item in outcomes
        if item.family == "SCALPING_STANDARD_H1_M15_M1"
    )
    if len(fast_raw) != EXPECTED_FAST_RAW:
        raise ValueError("fast-fractal fixed-selection count mismatch")
    if len(standard_raw) != EXPECTED_STANDARD_RAW:
        raise ValueError("scalping-standard fixed-selection count mismatch")

    fast_max3 = _max3(fast_raw)
    standard_max3 = _max3(standard_raw)
    fast_keys = {_entry_key(item) for item in fast_raw}
    standard_keys = {_entry_key(item) for item in standard_raw}
    exact_overlap = fast_keys & standard_keys

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        fast_slice = tuple(
            item for item in fast_max3 if item.session == session.value
        )
        standard_slice = tuple(
            item for item in standard_max3 if item.session == session.value
        )
        per_session[session.value] = {
            "fast_trades": len(fast_slice),
            "fast_metrics": (
                None if not fast_slice else _metrics(fast_slice)
            ),
            "standard_trades": len(standard_slice),
            "standard_metrics": (
                None if not standard_slice else _metrics(standard_slice)
            ),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": len(reports),
        "target_r": str(TARGET_R),
        "fast_raw_trades": len(fast_raw),
        "fast_max3_trades": len(fast_max3),
        "fast_max3_metrics": _metrics(fast_max3),
        "standard_raw_trades": len(standard_raw),
        "standard_max3_trades": len(standard_max3),
        "standard_max3_metrics": _metrics(standard_max3),
        "exact_entry_overlap_between_families": len(exact_overlap),
        "per_session": per_session,
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "only_target_r_changed": True,
        "new_entries_allowed": False,
        "cross_family_union_promoted": False,
        "development_window_role": "CONSUMED_LABORATORY",
        "fresh_holdout_claimed": False,
        "outcome_used_for_admission": False,
        "automatic_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_market(
    report: dict[str, Any],
    outcomes: tuple[AlternateTargetOutcome, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-alternate-families-target1-1y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-outcomes.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for outcome in outcomes:
            handle.write(json.dumps(asdict(outcome), sort_keys=True) + "\n")


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-alternate-families-target1-1y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("fast_root", type=Path)
    market.add_argument("standard_root", type=Path)
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
            args.fast_root,
            args.standard_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, outcomes, args.output)
        print(
            json.dumps(
                {
                    "identity": report["identity"],
                    "symbol": report["symbol"],
                    "fast_fixed_entries": report["fast_fixed_entries"],
                    "standard_fixed_entries": report["standard_fixed_entries"],
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
