"""Post-third-slot pre-entry atlas for Capitalizer 2Y.

The first causal Journey diagnostic removes, for analysis only, the frozen
31-trade cohort of third-slot candidates arriving after both earlier same-session
positions had already closed. That leaves 917 trades at 6.5896R DD.

This module asks whether one *orthogonal* causal pre-entry state among the same
already-audited stop-risk features explains the remaining drawdown. Every cell is
evaluated on the 917-trade diagnostic base. No cell is selected or promoted.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2y_v1 as stoprisk,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_POST_THIRD_SLOT_PREENTRY_ATLAS_2Y_V1"
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _load_binding(root: Path) -> tuple[dict[str, Any], ...]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("post-third-slot atlas requires one V2 binding artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("unexpected V2 binding identity")
    coverage = report.get("binding_coverage")
    if not isinstance(coverage, dict):
        raise ValueError("V2 binding coverage missing")
    if int(coverage.get("source_microstructure", -1)) != int(
        report.get("control_trades", -2)
    ):
        raise ValueError("post-third-slot atlas requires complete source binding")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("post-third-slot atlas rejects future evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("binding row must be object")
                rows.append(raw)
    return tuple(rows)


def _metrics(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
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
        "trades": len(rows),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(str(row["exit_reason"]) == "STOP" for row in rows),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def build_report(binding_root: Path, target_root: Path) -> dict[str, Any]:
    bindings = _load_binding(binding_root)
    control = binding_v1._load_control(target_root)
    binding_by_key = {_join_key(row): row for row in bindings}
    if len(binding_by_key) != len(bindings):
        raise ValueError("post-third-slot binding identity not unique")
    if {_join_key(row) for row in control} != set(binding_by_key):
        raise ValueError("post-third-slot binding/control identities differ")

    first_stage_blocked = tuple(
        row
        for row in control
        if int(binding_by_key[_join_key(row)]["prior_same_session_selected"]) == 2
        and int(binding_by_key[_join_key(row)]["baseline_active_positions"]) == 0
    )
    if len(first_stage_blocked) != 31:
        raise ValueError("expected frozen 31-trade first-stage diagnostic cohort")
    first_stage_keys = {_join_key(row) for row in first_stage_blocked}
    base = tuple(row for row in control if _join_key(row) not in first_stage_keys)
    if len(base) != 917:
        raise ValueError("post-third-slot diagnostic base must contain 917 trades")

    members: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for trade in base:
        binding = binding_by_key[_join_key(trade)]
        for cell in stoprisk._causal_cells(binding):
            members[cell].append(trade)

    base_stops = sum(str(row["exit_reason"]) == "STOP" for row in base)
    base_wins = sum(Decimal(str(row["realized_gross_r"])) > 0 for row in base)
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (feature, value), selected in members.items():
        blocked = tuple(selected)
        blocked_keys = {_join_key(row) for row in blocked}
        kept = tuple(row for row in base if _join_key(row) not in blocked_keys)
        blocked_stops = sum(str(row["exit_reason"]) == "STOP" for row in blocked)
        blocked_wins = sum(
            Decimal(str(row["realized_gross_r"])) > 0 for row in blocked
        )
        cells[feature].append(
            {
                "value": value,
                "blocked_trades": len(blocked),
                "blocked_metrics": _metrics(blocked),
                "blocked_stops": blocked_stops,
                "blocked_wins": blocked_wins,
                "base_stop_capture_rate": (
                    "0"
                    if base_stops == 0
                    else str(Decimal(blocked_stops) / Decimal(base_stops))
                ),
                "base_winner_sacrifice_rate": (
                    "0"
                    if base_wins == 0
                    else str(Decimal(blocked_wins) / Decimal(base_wins))
                ),
                "kept_trades": len(kept),
                "kept_metrics": _metrics(kept),
                "density_retention_vs_control": str(
                    Decimal(len(kept)) / Decimal(len(control))
                ),
                "density_retention_vs_917_base": str(
                    Decimal(len(kept)) / Decimal(len(base))
                ),
            }
        )

    return {
        "identity": IDENTITY,
        "source_binding_run_id": SOURCE_BINDING_RUN_ID,
        "source_binding_sha": SOURCE_BINDING_SHA,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "control_trades": len(control),
        "control_metrics": _metrics(control),
        "first_stage_diagnostic_hypothesis": (
            "ABSTAIN_THIRD_SLOT_WHEN_TWO_PRIOR_SESSION_SELECTIONS_"
            "ARE_BOTH_CLOSED_AT_DECISION"
        ),
        "first_stage_diagnostic_only": True,
        "first_stage_blocked_trades": len(first_stage_blocked),
        "base_trades": len(base),
        "base_metrics": _metrics(base),
        "feature_cells": {
            feature: sorted(rows, key=lambda row: str(row["value"]))
            for feature, rows in sorted(cells.items())
        },
        "feature_count": len(cells),
        "all_second_stage_features_known_by_entry": True,
        "current_outcome_used_to_create_second_stage_cells": False,
        "current_outcome_used_for_post_cell_metrics": True,
        "second_stage_cell_selected": False,
        "sequential_rule_promotion_allowed": False,
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
        "next_phase": "FALSIFY_ORTHOGONAL_PREENTRY_INFORMATION_VALUE_AFTER_THIRD_SLOT_DIAGNOSTIC",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-post-third-slot-preentry-atlas-2y-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binding_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.binding_root, args.target_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
