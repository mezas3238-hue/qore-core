"""Pre-entry stop-risk atlas on the true-2R Capitalizer cognitive rebase.

Consumes QORE_CAPITALIZER_COGNITIVE_ECONOMIC_REBASE_2R_V1. All causal
microstructure and dynamic portfolio/Journey fields therefore correspond to the
true 2R lifecycle. Current outcomes are used only after causal feature cells are
constructed.

This is consumed-window diagnostic research only. No cell is selected/promoted.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2y_v1 as stoprisk_v1,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_PREENTRY_STOP_RISK_ATLAS_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-economic-rebase-2r-v1.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("2R stop-risk atlas requires one rebase artifact")

    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != rebase.IDENTITY:
        raise ValueError("unexpected 2R rebase identity")
    if str(report.get("target_r")) != "2.00":
        raise ValueError("2R stop-risk atlas requires target_r=2.00")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("2R rebase row must be object")
                rows.append(raw)
    if len(rows) != rebase.EXPECTED_TRADES:
        raise ValueError("2R stop-risk population mismatch")
    return report, tuple(rows)


def _trade(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(row["symbol"]),
        "session": str(row["session"]),
        "operating_date": str(row["operating_date"]),
        "side": str(row["side"]),
        "entry_at": str(row["entry_at"]),
        "exit_at": str(row["post_audit_exit_at"]),
        "realized_gross_r": str(row["post_audit_realized_gross_r"]),
        "exit_reason": str(row["post_audit_exit_reason"]),
    }


def _metrics(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    ordered = tuple(
        sorted(
            rows,
            key=lambda row: (
                datetime.fromisoformat(str(row["entry_at"])),
                str(row["symbol"]),
            ),
        )
    )
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in ordered)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trades": len(ordered),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(str(row["exit_reason"]) == "STOP" for row in ordered),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def build_report(root: Path) -> dict[str, Any]:
    rebase_report, rows = _load_rebase(root)
    trades = tuple(_trade(row) for row in rows)
    trade_by_key = {_join_key(row): row for row in trades}
    if len(trade_by_key) != len(trades):
        raise ValueError("2R stop-risk trade identity not unique")

    members: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        trade = trade_by_key[_join_key(row)]
        for cell in stoprisk_v1._causal_cells(row):
            members[cell].append(trade)

    total_stops = sum(str(row["exit_reason"]) == "STOP" for row in trades)
    total_wins = sum(Decimal(str(row["realized_gross_r"])) > 0 for row in trades)
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (feature, value), selected in members.items():
        blocked = tuple(selected)
        blocked_keys = {_join_key(row) for row in blocked}
        kept = tuple(
            row for row in trades if _join_key(row) not in blocked_keys
        )
        blocked_stops = sum(
            str(row["exit_reason"]) == "STOP" for row in blocked
        )
        blocked_wins = sum(
            Decimal(str(row["realized_gross_r"])) > 0 for row in blocked
        )
        cells[feature].append(
            {
                "value": value,
                "trades": len(blocked),
                "stops": blocked_stops,
                "wins": blocked_wins,
                "losses": sum(
                    Decimal(str(row["realized_gross_r"])) < 0 for row in blocked
                ),
                "cell_metrics": _metrics(blocked),
                "counterfactual_if_abstained_metrics": _metrics(kept),
                "stop_capture_rate": (
                    "0"
                    if total_stops == 0
                    else str(Decimal(blocked_stops) / Decimal(total_stops))
                ),
                "winner_sacrifice_rate": (
                    "0"
                    if total_wins == 0
                    else str(Decimal(blocked_wins) / Decimal(total_wins))
                ),
                "density_retention_if_abstained": str(
                    Decimal(len(kept)) / Decimal(len(trades))
                ),
            }
        )

    absolute_dd_ceiling = Decimal("6")
    cells_under_dd_ceiling = sum(
        Decimal(str(row["counterfactual_if_abstained_metrics"]["max_drawdown_r"]))
        <= absolute_dd_ceiling
        for feature_rows in cells.values()
        for row in feature_rows
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(trades),
        "control_stops": total_stops,
        "control_metrics": _metrics(trades),
        "feature_cells": {
            feature: sorted(value, key=lambda row: str(row["value"]))
            for feature, value in sorted(cells.items())
        },
        "feature_count": len(cells),
        "counterfactual_cells_at_or_below_6r_dd": cells_under_dd_ceiling,
        "all_cell_features_known_by_entry": True,
        "dynamic_state_from_true_2r_rebase": True,
        "current_outcome_used_to_create_cells": False,
        "current_outcome_used_for_post_cell_metrics": True,
        "single_cell_counterfactuals_are_diagnostic_only": True,
        "cell_selected_for_enforcement": False,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(trades)
        ),
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "CROSS_FALSIFY_TRUE_2R_STOP_RISK_WITH_JOURNEY_STATE",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-preentry-stop-risk-atlas-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.rebase_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
