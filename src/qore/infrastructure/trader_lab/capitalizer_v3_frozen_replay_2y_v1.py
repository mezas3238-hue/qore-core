"""Exact frozen V3 replay over the Owner-selected 2Y diagnostic window.

This module is only a window adapter. It calls the frozen V3 market replay directly and
restores the original module window afterward. No V3 strategy rule is reimplemented here.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession

IDENTITY = "QORE_CAPITALIZER_V3_FROZEN_REPLAY_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_FROZEN_REPLAY_2Y_V1"
WINDOW_START = datetime(2024, 9, 17, 0, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
LOOKBACK_START = WINDOW_START - timedelta(days=21)


@contextmanager
def _v3_window() -> Iterator[None]:
    mutable_v3: Any = v3
    old_start = mutable_v3.WINDOW_START
    old_end = mutable_v3.WINDOW_END
    old_lookback = mutable_v3.LOOKBACK_START
    try:
        mutable_v3.WINDOW_START = WINDOW_START
        mutable_v3.WINDOW_END = WINDOW_END
        mutable_v3.LOOKBACK_START = LOOKBACK_START
        yield
    finally:
        mutable_v3.WINDOW_START = old_start
        mutable_v3.WINDOW_END = old_end
        mutable_v3.LOOKBACK_START = old_lookback


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[v3.V3Trade, ...]]:
    with _v3_window():
        source_report, trades = v3.build_market_report(m1_root, session=session)

    report = asdict(source_report)
    report.update(
        {
            "identity": IDENTITY,
            "source_strategy_identity": v3.IDENTITY,
            "window_start": WINDOW_START.isoformat(),
            "window_end_exclusive": WINDOW_END.isoformat(),
            "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
            "strategy_mutated": False,
            "entry_contract_changed": False,
            "stop_contract_changed": False,
            "target_contract_changed": False,
            "max3_contract_changed": False,
            "outcome_used_for_selection": False,
            "fresh_holdout_claimed": False,
            "economic_candidate": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
        }
    )
    return report, trades


def write_market(
    report: dict[str, Any],
    trades: tuple[v3.V3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-frozen-replay-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-v3-frozen-replay-2y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"V3 2Y matrix requires 9 reports, got {len(paths)}")
    reports = [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    if {str(item["symbol"]) for item in reports} != v3.EXPECTED_SYMBOLS:
        raise ValueError("V3 2Y universe mismatch")
    return reports


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    for path in sorted(root.rglob("capitalizer-*-v3-frozen-replay-2y-v1-trades.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
        )
    )


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = v3._portfolio_max3(raw)
    raw_metrics = v3._metrics(raw)
    max3_metrics = v3._metrics(max3)

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        session_raw = tuple(item for item in raw if item.session == session.value)
        session_max3 = tuple(item for item in max3 if item.session == session.value)
        raw_value = v3._metrics(session_raw)
        max3_value = v3._metrics(session_max3)
        per_session[session.value] = {
            "raw_trades": len(session_raw),
            "raw_metrics": None if raw_value is None else asdict(raw_value),
            "max3_trades": len(session_max3),
            "max3_metrics": None if max3_value is None else asdict(max3_value),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "source_strategy_identity": v3.IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "m5_closebacks_confirmed": sum(
            int(item["m5_closebacks_confirmed"]) for item in reports
        ),
        "m3_mss_confirmed": sum(int(item["m3_mss_confirmed"]) for item in reports),
        "m1_causal_fvg_confirmed": sum(
            int(item["m1_causal_fvg_confirmed"]) for item in reports
        ),
        "raw_trades": len(raw),
        "raw_metrics": None if raw_metrics is None else asdict(raw_metrics),
        "max3_selected_trades": len(max3),
        "max3_metrics": None if max3_metrics is None else asdict(max3_metrics),
        "max3_stop_exits": sum(item.exit_reason == "STOP" for item in max3),
        "max3_target_exits": sum(item.exit_reason == "TARGET" for item in max3),
        "max3_time_exits": sum(item.exit_reason == "TIME_EXIT" for item in max3),
        "max3_session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in max3
        ),
        "days_with_any_trade": len({item.operating_date for item in max3}),
        "per_session": per_session,
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "entry_identity": v3.ENTRY_IDENTITY,
        "stop_identity": v3.STOP_IDENTITY,
        "target_identity": v3.TARGET_IDENTITY,
        "diagnostic_window_role": "CONSUMED_DIAGNOSTIC_RESEARCH",
        "strategy_mutated": False,
        "entry_contract_changed": False,
        "stop_contract_changed": False,
        "target_contract_changed": False,
        "max3_contract_changed": False,
        "outcome_used_for_selection": False,
        "fresh_holdout_claimed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(
    report: dict[str, Any],
    output: Path,
    *,
    source_root: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-frozen-replay-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    max3 = v3._portfolio_max3(_load_trades(source_root))
    ledger = output / "capitalizer-nine-market-v3-frozen-replay-2y-v1-max3-trades.jsonl"
    with ledger.open("w", encoding="utf-8") as handle:
        for trade in max3:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


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
                    "symbol": report["symbol"],
                    "session": report["session"],
                    "entries_executed": report["entries_executed"],
                    "m3_mss_confirmed": report["m3_mss_confirmed"],
                    "m1_causal_fvg_confirmed": report["m1_causal_fvg_confirmed"],
                },
                sort_keys=True,
            )
        )
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output, source_root=args.input_root)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
