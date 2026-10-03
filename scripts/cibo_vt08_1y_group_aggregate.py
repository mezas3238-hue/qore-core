#!/usr/bin/env python3
"""Aggregate frozen VT08 B01 backtests into one fixed 1Y 3x1Y group lane."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.cibo_three_holdout_1y_contract import (
    expected_windows,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import AUTHORIZED_FOREX_MARKETS

PORTFOLIO = {
    ("AUDJPY", "short"),
    ("GBPUSD", "short"),
    ("GBPJPY", "long"),
    ("GBPJPY", "short"),
}


def _window(group_id: str) -> tuple[datetime, datetime]:
    for item in expected_windows():
        if item.group_id == group_id:
            return item.start_at, item.end_exclusive_at
    raise ValueError(group_id)


def aggregate(
    *,
    group_id: str,
    reports: tuple[Path, ...],
) -> dict[str, Any]:
    if len(reports) != len(AUTHORIZED_FOREX_MARKETS):
        raise ValueError("exact seven VT08 Forex backtests required")
    start_at, end_at = _window(group_id)
    seen: set[str] = set()
    methodology: set[str] = set()
    trades: list[dict[str, Any]] = []

    for path in reports:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != "qore.trader_lab.vt08_b01_backtest.r3.8.v1":
            raise ValueError("unexpected VT08 backtest schema")
        symbol = str(payload["symbol"])
        seen.add(symbol)
        methodology.add(str(payload["methodology_fingerprint"]))
        for raw in payload["trades"]:
            signal_at = datetime.fromisoformat(str(raw["signal_at"]))
            side = str(raw["side"])
            if start_at <= signal_at < end_at and (symbol, side) in PORTFOLIO:
                row = dict(raw)
                row["symbol"] = symbol
                trades.append(row)

    if seen != set(AUTHORIZED_FOREX_MARKETS):
        raise ValueError("VT08 seven-market surface incomplete")
    if len(methodology) != 1:
        raise ValueError("VT08 methodology drift across symbols")
    trades.sort(key=lambda row: (row["signal_at"], row["symbol"], row["side"]))
    values = [Decimal(str(row["return_rate"])) for row in trades]
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]
    gross_profit = sum(wins, Decimal(0))
    gross_loss = -sum(losses, Decimal(0))
    equity = Decimal(1)
    peak = equity
    max_dd = Decimal(0)
    for value in values:
        equity *= Decimal(1) + value
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)

    return {
        "schema": "qore.cibo.trader-lab.vt08-1y-group-lane.v1",
        "group_id": group_id,
        "trader_id": "VT08_FOREX",
        "start_at": start_at.isoformat(),
        "end_exclusive_at": end_at.isoformat(),
        "methodology_fingerprint": next(iter(methodology)),
        "portfolio": "B_COMBINED",
        "market_count": len(seen),
        "sample_size": len(values),
        "wins": len(wins),
        "losses": len(losses),
        "mean_return": format(
            sum(values, Decimal(0)) / Decimal(len(values))
            if values else Decimal(0),
            "f",
        ),
        "profit_factor": (
            None if gross_loss == 0 else format(gross_profit / gross_loss, "f")
        ),
        "compounded_return": format(equity - Decimal(1), "f"),
        "maximum_drawdown": format(max_dd, "f"),
        "trades": trades,
        "governance": {
            "methodology_changed": False,
            "outcome_aware_selection": False,
            "adaptive_research_only": True,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--group-id",
        choices=("GROUP_1", "GROUP_2", "GROUP_3"),
        required=True,
    )
    parser.add_argument("--report", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = aggregate(group_id=args.group_id, reports=tuple(args.report))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "group_id": args.group_id,
                "sample_size": payload["sample_size"],
                "profit_factor": payload["profit_factor"],
                "compounded_return": payload["compounded_return"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
