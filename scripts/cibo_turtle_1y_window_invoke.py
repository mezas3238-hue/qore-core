#!/usr/bin/env python3
"""Invoke an immutable Turtle geometry replay on one fixed 1Y research window.

Only EVAL_OPEN/EVAL_CLOSE are changed in memory. Frozen strategy rules,
families, target logic, memory, risk governor and geometry code remain intact.
The original module is never modified on disk.
"""

from __future__ import annotations

import argparse
import importlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.cibo_three_holdout_1y_contract import (
    expected_windows,
)


def _window(group_id: str) -> tuple[datetime, datetime]:
    for item in expected_windows():
        if item.group_id == group_id:
            return item.start_at, item.end_exclusive_at
    raise ValueError(group_id)


def _pf(values: list[Decimal]) -> Decimal | None:
    gains = sum((x for x in values if x > 0), Decimal(0))
    losses = -sum((x for x in values if x < 0), Decimal(0))
    return None if losses == 0 else gains / losses


def _dd(values: list[Decimal]) -> Decimal:
    equity = peak = worst = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def invoke(
    *,
    module_name: str,
    trader_id: str,
    symbol: str,
    group_id: str,
    raw_root: Path,
    target_root: Path,
    memory_root: Path,
    freeze_root: Path,
    output: Path,
) -> dict[str, Any]:
    start_at, end_at = _window(group_id)
    module = importlib.import_module(module_name)

    if not hasattr(module, "EVAL_OPEN") or not hasattr(module, "EVAL_CLOSE"):
        raise ValueError("geometry module lacks evaluation-window constants")
    original_open = module.EVAL_OPEN
    original_close = module.EVAL_CLOSE
    r3 = getattr(module, "r3", None)
    r3_original: tuple[datetime, datetime] | None = None
    if r3 is not None:
        if not hasattr(r3, "EVAL_OPEN") or not hasattr(r3, "EVAL_CLOSE"):
            raise ValueError("geometry r3 dependency lacks evaluation-window constants")
        r3_original = (r3.EVAL_OPEN, r3.EVAL_CLOSE)

    output.mkdir(parents=True, exist_ok=True)
    try:
        module.EVAL_OPEN = start_at
        module.EVAL_CLOSE = end_at
        if r3 is not None:
            r3.EVAL_OPEN = start_at
            r3.EVAL_CLOSE = end_at
        report = module.run(
            raw_root,
            target_root,
            memory_root,
            freeze_root,
            output,
        )
    finally:
        module.EVAL_OPEN = original_open
        module.EVAL_CLOSE = original_close
        if r3 is not None and r3_original is not None:
            r3.EVAL_OPEN, r3.EVAL_CLOSE = r3_original

    trade_paths = tuple(output.glob("*geometry-trades.jsonl"))
    if len(trade_paths) != 1:
        raise ValueError(
            f"expected exact one serialized geometry ledger, got {len(trade_paths)}"
        )
    rows = [
        json.loads(line)
        for line in trade_paths[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError(f"{trader_id}:{group_id} produced zero geometry trades")
    for row in rows:
        entry = datetime.fromisoformat(str(row["entry_at"]))
        if not start_at <= entry < end_at:
            raise ValueError("geometry replay emitted entry outside frozen group")

    raw_values = [Decimal(str(row["raw_net_010_r"])) for row in rows]
    scaled_values = [
        Decimal(str(row.get("scaled_net_010_r", row["raw_net_010_r"])))
        for row in rows
    ]
    raw_pf = _pf(raw_values)
    scaled_pf = _pf(scaled_values)
    lane = {
        "schema": "qore.cibo.trader-lab.turtle-1y-group-lane.v1",
        "group_id": group_id,
        "trader_id": trader_id,
        "symbol": symbol,
        "start_at": start_at.isoformat(),
        "end_exclusive_at": end_at.isoformat(),
        "geometry_module": module_name,
        "sample_size": len(rows),
        "raw_structural": {
            "total_r": format(sum(raw_values, Decimal(0)), "f"),
            "expectancy_r": format(
                sum(raw_values, Decimal(0)) / Decimal(len(raw_values)),
                "f",
            ),
            "profit_factor": None if raw_pf is None else format(raw_pf, "f"),
            "max_drawdown_r": format(_dd(raw_values), "f"),
        },
        "legacy_scaled_diagnostic": {
            "total_r": format(sum(scaled_values, Decimal(0)), "f"),
            "profit_factor": (
                None if scaled_pf is None else format(scaled_pf, "f")
            ),
            "max_drawdown_r": format(_dd(scaled_values), "f"),
            "used_for_cibo_sizing": False,
        },
        "module_report": report,
        "trades": rows,
        "governance": {
            "window_only_parameterized": True,
            "trader_methodology_changed": False,
            "trader_legacy_sizing_used_for_cibo": False,
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
    (output / "trader-lab-1y-group-lane.json").write_text(
        json.dumps(lane, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return lane


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", required=True)
    parser.add_argument("--trader-id", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument(
        "--group-id",
        choices=("GROUP_1", "GROUP_2", "GROUP_3"),
        required=True,
    )
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--memory-root", type=Path, required=True)
    parser.add_argument("--freeze-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lane = invoke(
        module_name=args.module,
        trader_id=args.trader_id,
        symbol=args.symbol,
        group_id=args.group_id,
        raw_root=args.raw_root,
        target_root=args.target_root,
        memory_root=args.memory_root,
        freeze_root=args.freeze_root,
        output=args.output,
    )
    print(
        json.dumps(
            {
                "group_id": lane["group_id"],
                "trader_id": lane["trader_id"],
                "sample_size": lane["sample_size"],
                "raw_structural": lane["raw_structural"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
