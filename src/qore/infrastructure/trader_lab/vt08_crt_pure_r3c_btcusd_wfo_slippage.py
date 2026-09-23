"""R3-C fixed-candidate walk-forward and execution-slippage stress for BTCUSD.

The candidate is already frozen as VT08_CRT_PURE_BTCUSD_R3_REF2_PLUS_001.
No parameter is re-fit between folds.

Walk-forward characterization:
- nine chronological Sep-to-Sep folds;
- each fold must have >=10 trades;
- each fold must have positive Total-R;
- each fold DD must remain <=8R.

Execution slippage stress:
- applies adverse slippage independently to entry and exit;
- slippage is expressed as a fraction of the original structural risk distance;
- absolute stop and target structure are not widened/moved;
- stressed R is recomputed using the worsened entry risk denominator.

Frozen per-fill stress family:
- 0.01R;
- 0.025R;
- 0.05R.

Gate:
- 0.025R/fill remains positive with PF >=1.20;
- 0.05R/fill remains positive.

Research/certification only. No deployment authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r3a_btcusd_chronological import (
    CANDIDATE_IDENTITY,
    run_replay,
)

IDENTITY = "VT08_CRT_PURE_BTCUSD_R3C_WFO_SLIPPAGE_001"
SCHEMA = "qore.vt08.crt_pure.r3c_btcusd_wfo_slippage.v1"

MIN_FOLD_TRADES = 10
MAX_FOLD_DD_R = 8.0
SLIPPAGE_PER_FILL: tuple[Decimal, ...] = (
    Decimal("0.01"),
    Decimal("0.025"),
    Decimal("0.05"),
)
MID_STRESS_MIN_PF = 1.20


def _stressed_r(trade: Model1LabTrade, per_fill_fraction: Decimal) -> Decimal:
    entry = Decimal(str(trade.entry_price_relative))
    stop = Decimal(str(trade.stop_price_relative))
    exit_price = Decimal(str(trade.exit_price_relative))
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("slippage stress requires positive original risk")

    slip = per_fill_fraction * risk
    if trade.parent_direction == "BULLISH":
        stressed_entry = entry + slip
        stressed_exit = exit_price - slip
        stressed_risk = stressed_entry - stop
        pnl = stressed_exit - stressed_entry
    elif trade.parent_direction == "BEARISH":
        stressed_entry = entry - slip
        stressed_exit = exit_price + slip
        stressed_risk = stop - stressed_entry
        pnl = stressed_entry - stressed_exit
    else:
        raise ValueError(f"unsupported parent direction: {trade.parent_direction}")

    if stressed_risk <= 0:
        raise ValueError("adverse slippage produced non-positive structural risk")
    return pnl / stressed_risk


def _summary_values(values: tuple[Decimal, ...]) -> dict[str, Any]:
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flat = len(values) - wins - losses
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
    pf = None if gross_loss == 0 else gross_profit / gross_loss

    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    longest = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 0

    total = sum(values, Decimal("0"))
    return {
        "trades": len(values),
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "profit_factor": None if pf is None else round(float(pf), 8),
        "total_r": round(float(total), 8),
        "mean_r": 0.0 if not values else round(float(total / Decimal(len(values))), 8),
        "max_drawdown_r": round(float(max_dd), 8),
        "longest_losing_streak": longest,
    }


def _slippage_summary(
    trades: tuple[Model1LabTrade, ...],
    per_fill_fraction: Decimal,
) -> dict[str, Any]:
    values = tuple(_stressed_r(trade, per_fill_fraction) for trade in trades)
    summary = _summary_values(values)
    summary["slippage_r_fraction_per_fill"] = str(per_fill_fraction)
    summary["round_trip_nominal_fraction"] = str(per_fill_fraction * Decimal(2))
    return summary


def run_certification() -> tuple[tuple[Model1LabTrade, ...], dict[str, Any]]:
    trades, chronological = run_replay()

    annual = chronological["annual"]
    wfo_failures: list[str] = []
    for label, fold in annual.items():
        if int(fold["trades"]) < MIN_FOLD_TRADES:
            wfo_failures.append(f"{label}_MIN_TRADES")
        if float(fold["total_r"]) <= 0:
            wfo_failures.append(f"{label}_TOTAL_R")
        if float(fold["max_drawdown_r"]) > MAX_FOLD_DD_R:
            wfo_failures.append(f"{label}_MAX_DD")

    stress = {
        f"SLIP_{str(level).replace('.', '_')}R_PER_FILL": _slippage_summary(
            trades,
            level,
        )
        for level in SLIPPAGE_PER_FILL
    }
    mid = stress["SLIP_0_025R_PER_FILL"]
    high = stress["SLIP_0_05R_PER_FILL"]
    slippage_failures: list[str] = []
    mid_pf = mid["profit_factor"]
    if (
        float(mid["total_r"]) <= 0
        or mid_pf is None
        or float(mid_pf) < MID_STRESS_MIN_PF
    ):
        slippage_failures.append("MID_SLIPPAGE")
    if float(high["total_r"]) <= 0:
        slippage_failures.append("HIGH_SLIPPAGE")

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate_identity": CANDIDATE_IDENTITY,
        "candidate_frozen_before_r3c": True,
        "parameter_refit_between_folds": False,
        "walk_forward": {
            "folds": annual,
            "min_fold_trades": MIN_FOLD_TRADES,
            "max_fold_drawdown_r": MAX_FOLD_DD_R,
            "passed": not wfo_failures,
            "failures": wfo_failures,
        },
        "slippage": {
            "model": "ADVERSE_ENTRY_AND_EXIT_AS_FRACTION_OF_ORIGINAL_STRUCTURAL_RISK",
            "stop_target_structure_moved": False,
            "levels_per_fill": [str(level) for level in SLIPPAGE_PER_FILL],
            "mid_stress_min_pf": MID_STRESS_MIN_PF,
            "stress": stress,
            "passed": not slippage_failures,
            "failures": slippage_failures,
        },
        "r3a_chronological_passed": chronological["chronological_gate_passed"],
        "r3c_passed": (
            bool(chronological["chronological_gate_passed"])
            and not wfo_failures
            and not slippage_failures
        ),
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "research_only": True,
    }
    return trades, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    trades, report = run_certification()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "source_trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    print("CRT_R3C_BTC_WFO_SLIPPAGE_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
