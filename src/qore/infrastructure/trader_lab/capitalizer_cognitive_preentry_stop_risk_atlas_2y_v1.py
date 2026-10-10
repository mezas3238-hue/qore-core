"""Pre-entry stop-risk causal atlas for the frozen Capitalizer 2Y 1R set.

This consumed-window diagnostic asks where the 223 STOP outcomes concentrate among
facts that were already knowable at entry. It does not change the strategy, stop,
target, MAX3, or cognitive rules and does not promote a runtime filter.

Only categorical causal states are used. The single timing boundary (5 minutes)
is not fitted here; it is inherited from the already-frozen WAIT5 maturation
contract. Outcomes are attached only after causal cells are constructed.
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
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_PREENTRY_STOP_RISK_ATLAS_2Y_V1"
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"
WAIT5_MINUTES = 5


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _aware(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _load_binding(root: Path) -> tuple[dict[str, Any], ...]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("stop-risk atlas requires one V2 binding artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("unexpected V2 binding identity")
    coverage = report.get("binding_coverage")
    if not isinstance(coverage, dict):
        raise ValueError("V2 binding coverage missing")
    if int(coverage.get("source_microstructure", -1)) != int(
        report.get("control_trades", -2)
    ):
        raise ValueError("stop-risk atlas requires complete source binding")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("stop-risk atlas rejects future evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("V2 binding row must be object")
                rows.append(raw)
    return tuple(rows)


def _token_map(row: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in row.get("microstructure_observations", ()):
        token = str(raw)
        if ":" not in token:
            continue
        key, value = token.split(":", 1)
        if key in result and result[key] != value:
            raise ValueError(f"duplicate conflicting observation token: {key}")
        result[key] = value
    return result


def _timestamp_token(tokens: dict[str, str], *names: str) -> datetime | None:
    for name in names:
        value = tokens.get(name)
        if value is not None and value != "None":
            return _aware(value)
    return None


def _mss_phase(row: dict[str, Any], tokens: dict[str, str]) -> str:
    entry = _aware(row["entry_at"])
    mss = _timestamp_token(tokens, "NEW_MSS_AT", "M3_MSS_AT", "SOURCE_FIRST_MSS_AT")
    if mss is None:
        return "UNKNOWN"
    delta_minutes = Decimal(str((entry - mss).total_seconds())) / Decimal("60")
    if delta_minutes < 0:
        raise ValueError("MSS cannot occur after entry")
    return "EARLY_LT5M" if delta_minutes < WAIT5_MINUTES else "MATURE_GE5M"


def _fvg_phase(row: dict[str, Any], tokens: dict[str, str]) -> str:
    entry = _aware(row["entry_at"])
    fvg = _timestamp_token(tokens, "NEW_FVG_AT", "M1_FVG_CONFIRMED_AT")
    if fvg is None:
        return "UNKNOWN"
    delta = entry - fvg
    if delta.total_seconds() < 0:
        raise ValueError("FVG cannot confirm after entry")
    return "SAME_MINUTE" if delta.total_seconds() < 60 else "LATER_RETEST"


def _shared_factor_state(row: dict[str, Any]) -> str:
    same = tuple(row.get("baseline_same_direction_factors", ()))
    opposing = tuple(row.get("baseline_opposing_direction_factors", ()))
    if same and opposing:
        return "MIXED"
    if same:
        return "SAME_DIRECTION"
    if opposing:
        return "OPPOSING_DIRECTION"
    return "NONE"


def _causal_cells(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    tokens = _token_map(row)
    return (
        ("SYMBOL", str(row["symbol"])),
        ("SESSION", str(row["session"])),
        ("SIDE", str(row["side"])),
        ("PROVENANCE", str(row["provenance"])),
        ("SOURCE_FAMILY", str(row.get("source_microstructure_family"))),
        ("ENTRY_MODE", tokens.get("ENTRY_MODE", "UNKNOWN")),
        ("OB_FVG_OVERLAP", tokens.get("M1_OB_FVG_OVERLAP", "UNKNOWN")),
        ("LIQUIDITY_KIND", tokens.get("LIQUIDITY_KIND", "UNKNOWN")),
        ("LIQUIDITY_SOURCE", tokens.get("LIQUIDITY_SOURCE", "UNKNOWN")),
        ("WAIT5_ARMED", tokens.get("WAIT5_ARMED", "UNKNOWN")),
        ("MSS_TO_ENTRY_PHASE", _mss_phase(row, tokens)),
        ("FVG_TO_ENTRY_PHASE", _fvg_phase(row, tokens)),
        ("ACTIVE_POSITION_STATE", "ACTIVE" if int(row["baseline_active_positions"]) else "NONE"),
        ("SHARED_FACTOR_STATE", _shared_factor_state(row)),
        ("PRIOR_SAME_SESSION_SELECTED", str(row["prior_same_session_selected"])),
    )


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
    binding_rows = _load_binding(binding_root)
    control = binding_v1._load_control(target_root)
    if len(binding_rows) != len(control):
        raise ValueError("stop-risk binding/control population mismatch")

    binding_by_key = {_join_key(row): row for row in binding_rows}
    if len(binding_by_key) != len(binding_rows):
        raise ValueError("stop-risk binding identity not unique")
    if {_join_key(row) for row in control} != set(binding_by_key):
        raise ValueError("stop-risk binding/control identities differ")

    cell_members: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for trade in control:
        binding = binding_by_key[_join_key(trade)]
        for cell in _causal_cells(binding):
            cell_members[cell].append(trade)

    total_stops = sum(str(row["exit_reason"]) == "STOP" for row in control)
    total_wins = sum(Decimal(str(row["realized_gross_r"])) > 0 for row in control)
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (feature, value), members in cell_members.items():
        blocked = tuple(members)
        member_keys = {_join_key(row) for row in blocked}
        kept = tuple(row for row in control if _join_key(row) not in member_keys)
        blocked_stops = sum(str(row["exit_reason"]) == "STOP" for row in blocked)
        blocked_wins = sum(
            Decimal(str(row["realized_gross_r"])) > 0 for row in blocked
        )
        cells[feature].append(
            {
                "value": value,
                "trades": len(blocked),
                "stops": blocked_stops,
                "stop_rate": str(
                    Decimal(blocked_stops) / Decimal(len(blocked))
                ),
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
                    Decimal(len(kept)) / Decimal(len(control))
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
        "control_stops": total_stops,
        "feature_cells": {
            feature: sorted(rows, key=lambda row: str(row["value"]))
            for feature, rows in sorted(cells.items())
        },
        "feature_count": len(cells),
        "wait5_boundary_inherited_not_fitted": True,
        "all_cell_features_known_by_entry": True,
        "current_outcome_used_to_create_cells": False,
        "current_outcome_used_for_post_cell_metrics": True,
        "single_cell_counterfactuals_are_diagnostic_only": True,
        "cell_selected_for_enforcement": False,
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
        "next_phase": "FREEZE_ONLY_CAUSAL_HYPOTHESES_THAT_SURVIVE_CROSS_FEATURE_FALSIFICATION",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-preentry-stop-risk-atlas-2y-v1.json"
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
