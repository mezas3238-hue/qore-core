"""Causal diagnostics for the frozen VT08 CRT PURE 2Y baseline replay."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayTrade, summarize


@dataclass(frozen=True, slots=True)
class ForensicSlice:
    label: str
    trades: int
    wins: int
    losses: int
    profit_factor: float | None
    total_r: float
    mean_r: float | None
    max_drawdown_r: float
    longest_losing_streak: int
    target_50_exits: int
    stop_exits: int
    c3_close_exits: int


def _slice(label: str, trades: Iterable[ReplayTrade]) -> ForensicSlice:
    rows = tuple(sorted(trades, key=lambda item: item.c3_opened_at))
    s = summarize(rows)
    return ForensicSlice(
        label=label,
        trades=int(s["trades"]),
        wins=int(s["wins"]),
        losses=int(s["losses"]),
        profit_factor=s["profit_factor"],
        total_r=float(s["total_r"]),
        mean_r=s["mean_r"],
        max_drawdown_r=float(s["max_drawdown_r"]),
        longest_losing_streak=int(s["longest_losing_streak"]),
        target_50_exits=int(s["target_50_exits"]),
        stop_exits=int(s["stop_exits"]),
        c3_close_exits=int(s["c3_close_exits"]),
    )


def _rr_bucket(value: float) -> str:
    if value < 0.50:
        return "RR_LT_0_50"
    if value < 0.75:
        return "RR_0_50_TO_0_75"
    if value < 1.00:
        return "RR_0_75_TO_1_00"
    if value < 1.50:
        return "RR_1_00_TO_1_50"
    return "RR_GE_1_50"


def build_forensics(trades: tuple[ReplayTrade, ...]) -> dict[str, Any]:
    dimensions: dict[str, dict[str, list[ReplayTrade]]] = {
        "market": defaultdict(list),
        "timing_triplet": defaultdict(list),
        "direction": defaultdict(list),
        "exit_reason": defaultdict(list),
        "reward_to_midpoint_bucket": defaultdict(list),
        "market_x_triplet": defaultdict(list),
        "market_x_direction": defaultdict(list),
    }

    for trade in trades:
        dimensions["market"][trade.market].append(trade)
        dimensions["timing_triplet"][trade.timing_triplet].append(trade)
        dimensions["direction"][trade.direction].append(trade)
        dimensions["exit_reason"][trade.exit_reason].append(trade)
        rr_bucket = _rr_bucket(trade.reward_to_midpoint_r)
        dimensions["reward_to_midpoint_bucket"][rr_bucket].append(trade)
        dimensions["market_x_triplet"][f"{trade.market}|T{trade.timing_triplet}"].append(trade)
        dimensions["market_x_direction"][f"{trade.market}|{trade.direction}"].append(trade)

    reward_values = tuple(trade.reward_to_midpoint_r for trade in trades)
    return {
        "schema": "qore.vt08.crt_pure.2y_baseline_forensics.v1",
        "identity": "VT08_CRT_PURE_2Y_BASELINE_FORENSICS_001",
        "overall": asdict(_slice("ALL", trades)),
        "reward_to_midpoint": {
            "mean": None if not reward_values else sum(reward_values) / len(reward_values),
            "minimum": None if not reward_values else min(reward_values),
            "maximum": None if not reward_values else max(reward_values),
            "below_0_50_count": sum(value < 0.50 for value in reward_values),
            "below_0_75_count": sum(value < 0.75 for value in reward_values),
            "below_1_00_count": sum(value < 1.00 for value in reward_values),
            "at_least_1_00_count": sum(value >= 1.00 for value in reward_values),
        },
        "dimensions": {
            dimension: {
                label: asdict(_slice(label, rows))
                for label, rows in sorted(groups.items())
            }
            for dimension, groups in dimensions.items()
        },
        "research_only": True,
        "candidate_certified": False,
        "methodology_mutated": False,
    }


def load_ledgers(root: Path) -> tuple[ReplayTrade, ...]:
    paths = tuple(sorted(root.rglob("trades.jsonl")))
    if len(paths) != 3:
        raise RuntimeError(f"expected 3 market ledgers, found {len(paths)}")
    rows: list[ReplayTrade] = []
    for path in paths:
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(ReplayTrade(**json.loads(line)))
    return tuple(sorted(rows, key=lambda item: item.c3_opened_at))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    trades = load_ledgers(args.input)
    report = build_forensics(trades)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("CRT_2Y_FORENSICS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
