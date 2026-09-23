"""Outcome-aware descriptive forensics for selected WAIT5_LATE60 trades.

This module does not create or promote admission rules. It decomposes the already
consumed WAIT5_LATE60 2Y result to explain why the structurally clean late-fill
reservoir degraded portfolio economics.

Dimensions are predeclared from decision-time structure:
- delay after original H1 deadline;
- remaining lifecycle after entry;
- MSS-to-entry age;
- frozen fill mode;
- OB/FVG overlap;
- session and market as descriptive strata.

It also compares final LATE60 portfolio selection against the frozen WAIT5
portfolio to quantify which baseline trades were displaced by MAX3 competition.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_LATE60_FORENSICS_2Y_V1"
EXPECTED_LATE60_SELECTED = 354
EXPECTED_LATE60_PORTFOLIO = 1327
EXPECTED_WAIT5_PORTFOLIO = 983


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_late60(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-late60-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"late60 forensics requires 9 ledgers, got {len(paths)}")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return v3._portfolio_max3(
        tuple(sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol)))
    )


def _load_wait5(root: Path) -> tuple[v3.V3Trade, ...]:
    rows: list[v3.V3Trade] = []
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-wait5-2y-v1-trades.jsonl")
    )
    if len(paths) != 9:
        raise ValueError(f"late60 forensics requires 9 WAIT5 ledgers, got {len(paths)}")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return v3._portfolio_max3(
        tuple(sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol)))
    )


def _metrics(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(trades)
    return None if value is None else asdict(value)


def _trade_key(trade: v3.V3Trade) -> tuple[str, str, str, str, str]:
    return (
        trade.symbol,
        trade.session,
        trade.operating_date,
        trade.side,
        trade.entry_at,
    )


def _delay_minutes(trade: v3.V3Trade) -> int:
    extended = _aware(trade.h1_deadline)
    original = extended - timedelta(minutes=60)
    return int((_aware(trade.entry_at) - original).total_seconds() // 60)


def _remaining_minutes(trade: v3.V3Trade) -> int:
    return int(
        (_aware(trade.h1_deadline) - _aware(trade.entry_at)).total_seconds() // 60
    )


def _mss_age_minutes(trade: v3.V3Trade) -> int:
    return int(
        (_aware(trade.entry_at) - _aware(trade.m3_mss_at)).total_seconds() // 60
    )


def _band(value: int, cuts: tuple[int, ...]) -> str:
    previous = 0
    for cut in cuts:
        if value <= cut:
            return f"{previous:02d}_{cut:02d}M"
        previous = cut + 1
    return f"{previous:02d}M_PLUS"


def _group_metrics(
    trades: tuple[v3.V3Trade, ...],
    key_fn: Any,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[v3.V3Trade]] = defaultdict(list)
    for trade in trades:
        grouped[str(key_fn(trade))].append(trade)
    result: dict[str, dict[str, Any]] = {}
    for key, values in sorted(grouped.items()):
        cohort = tuple(values)
        result[key] = {
            "trades": len(cohort),
            "metrics": _metrics(cohort),
        }
    return result


def _drawdown_episode(
    trades: tuple[v3.V3Trade, ...],
) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda item: (_aware(item.exit_at), item.symbol))
    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = -1
    worst = Decimal("0")
    worst_peak_index = -1
    worst_trough_index = -1
    for index, trade in enumerate(ordered):
        equity += Decimal(trade.realized_gross_r)
        if equity > peak:
            peak = equity
            peak_index = index
        dd = peak - equity
        if dd > worst:
            worst = dd
            worst_peak_index = peak_index
            worst_trough_index = index
    if worst_trough_index < 0:
        return {"drawdown_r": "0", "trades": 0}

    start = worst_peak_index + 1
    episode = tuple(ordered[start : worst_trough_index + 1])
    late = tuple(t for t in episode if t.entry_mode.startswith("LATE60_"))
    baseline = tuple(t for t in episode if not t.entry_mode.startswith("LATE60_"))
    return {
        "drawdown_r": str(worst),
        "peak_exit_at": (
            None if worst_peak_index < 0 else ordered[worst_peak_index].exit_at
        ),
        "trough_exit_at": ordered[worst_trough_index].exit_at,
        "trades": len(episode),
        "late60_trades": len(late),
        "late60_metrics": _metrics(late),
        "baseline_metrics": _metrics(baseline),
        "by_session": _group_metrics(episode, lambda t: t.session),
        "by_market": _group_metrics(episode, lambda t: t.symbol),
    }


def build_report(late60_root: Path, wait5_root: Path) -> dict[str, Any]:
    late60_portfolio = _load_late60(late60_root)
    wait5_portfolio = _load_wait5(wait5_root)

    if len(late60_portfolio) != EXPECTED_LATE60_PORTFOLIO:
        raise ValueError("LATE60 portfolio control mismatch")
    if len(wait5_portfolio) != EXPECTED_WAIT5_PORTFOLIO:
        raise ValueError("WAIT5 portfolio control mismatch")

    selected_late = tuple(
        trade for trade in late60_portfolio if trade.entry_mode.startswith("LATE60_")
    )
    if len(selected_late) != EXPECTED_LATE60_SELECTED:
        raise ValueError("LATE60 selected control mismatch")

    late_keys = {_trade_key(item) for item in late60_portfolio}
    wait5_keys = {_trade_key(item) for item in wait5_portfolio}
    displaced_wait5 = tuple(
        item for item in wait5_portfolio if _trade_key(item) not in late_keys
    )
    added_keys = late_keys - wait5_keys

    return {
        "identity": IDENTITY,
        "late60_portfolio_trades": len(late60_portfolio),
        "wait5_portfolio_trades": len(wait5_portfolio),
        "selected_late60_trades": len(selected_late),
        "net_added_trade_keys_vs_wait5": len(added_keys),
        "displaced_wait5_trades": len(displaced_wait5),
        "late60_overall_metrics": _metrics(selected_late),
        "displaced_wait5_metrics": _metrics(displaced_wait5),
        "delay_after_deadline": _group_metrics(
            selected_late,
            lambda t: _band(_delay_minutes(t), (5, 15, 30, 45, 59)),
        ),
        "remaining_lifecycle": _group_metrics(
            selected_late,
            lambda t: _band(_remaining_minutes(t), (5, 15, 30, 45, 60)),
        ),
        "mss_to_entry_age": _group_metrics(
            selected_late,
            lambda t: _band(_mss_age_minutes(t), (30, 60, 90, 120)),
        ),
        "entry_mode": _group_metrics(selected_late, lambda t: t.entry_mode),
        "ob_fvg_overlap": _group_metrics(
            selected_late,
            lambda t: "OVERLAP" if t.m1_ob_fvg_overlap else "NO_OVERLAP",
        ),
        "session": _group_metrics(selected_late, lambda t: t.session),
        "market": _group_metrics(selected_late, lambda t: t.symbol),
        "exit_reason": _group_metrics(selected_late, lambda t: t.exit_reason),
        "portfolio_max_drawdown_episode": _drawdown_episode(late60_portfolio),
        "outcome_aware_descriptive_only": True,
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-v3-source-first-wait5-late60-forensics-2y-v1.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("late60_root", type=Path)
    parser.add_argument("wait5_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.late60_root, args.wait5_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
