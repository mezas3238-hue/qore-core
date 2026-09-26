"""Cross-feature falsification for Capitalizer third-slot candidates.

This consumed-window diagnostic intersects the already-audited causal Journey
state of the 40 frozen third-slot candidates with the already-audited pre-entry
stop-risk state. It deliberately performs exhaustive *two-way* intersections of:

- one Journey feature; and
- one pre-entry stop-risk feature.

No pair is selected, promoted, or granted runtime authority here. The current
candidate outcome is attached only after the causal cell key is constructed.

The purpose is to falsify broad third-slot hypotheses and identify whether the
poor 31-trade cohort (third slot with no active earlier position) can be
explained by a narrower causal state without destroying PF or density.
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
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_third_slot_journey_atlas_2y_v1 as journey,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_THIRD_SLOT_CROSS_FEATURE_ATLAS_2Y_V1"
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"

JOURNEY_FEATURES = (
    "PRIOR_TWO_STATE",
    "PRIOR_SESSION_REALIZED_SIGN",
    "PRIOR_DAY_REALIZED_SIGN",
    "PRIOR_SESSION_CLOSED_COUNT",
    "MOST_RECENT_CLOSED_SESSION_OUTCOME",
    "ACTIVE_POSITION_COUNT",
)
PREENTRY_FEATURES = (
    "SYMBOL",
    "SESSION",
    "SIDE",
    "PROVENANCE",
    "SOURCE_FAMILY",
    "ENTRY_MODE",
    "OB_FVG_OVERLAP",
    "LIQUIDITY_KIND",
    "LIQUIDITY_SOURCE",
    "WAIT5_ARMED",
    "MSS_TO_ENTRY_PHASE",
    "FVG_TO_ENTRY_PHASE",
    "ACTIVE_POSITION_STATE",
    "SHARED_FACTOR_STATE",
)


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
        raise ValueError("cross-feature atlas requires one V2 binding artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("unexpected V2 binding identity")
    coverage = report.get("binding_coverage")
    if not isinstance(coverage, dict):
        raise ValueError("V2 binding coverage missing")
    if int(coverage.get("source_microstructure", -1)) != int(
        report.get("control_trades", -2)
    ):
        raise ValueError("cross-feature atlas requires complete source binding")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("cross-feature atlas rejects future evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("V2 binding row must be object")
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


def _cell_map(cells: tuple[tuple[str, str], ...]) -> dict[str, str]:
    result = dict(cells)
    if len(result) != len(cells):
        raise ValueError("duplicate causal feature name")
    return result


def build_report(binding_root: Path, target_root: Path) -> dict[str, Any]:
    bindings = _load_binding(binding_root)
    control = binding_v1._load_control(target_root)
    binding_by_key = {_join_key(row): row for row in bindings}
    if len(binding_by_key) != len(bindings):
        raise ValueError("cross-feature binding identity not unique")
    if {_join_key(row) for row in control} != set(binding_by_key):
        raise ValueError("cross-feature binding/control identities differ")

    third = tuple(
        row
        for row in control
        if int(binding_by_key[_join_key(row)]["prior_same_session_selected"]) == 2
    )
    if len(third) != 40:
        raise ValueError(f"expected frozen 40 third-slot trades, got {len(third)}")

    members: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in third:
        binding = binding_by_key[_join_key(candidate)]
        journey_cells = _cell_map(
            journey._causal_cells(
                candidate=candidate,
                binding=binding,
                control=control,
            )
        )
        preentry_cells = _cell_map(stoprisk._causal_cells(binding))

        if tuple(journey_cells) != JOURNEY_FEATURES:
            raise ValueError("Journey feature contract drifted")
        for feature in PREENTRY_FEATURES:
            if feature not in preentry_cells:
                raise ValueError(f"missing pre-entry feature: {feature}")

        for journey_feature in JOURNEY_FEATURES:
            for preentry_feature in PREENTRY_FEATURES:
                members[
                    (
                        journey_feature,
                        journey_cells[journey_feature],
                        preentry_feature,
                        preentry_cells[preentry_feature],
                    )
                ].append(candidate)

    total_stops = sum(str(row["exit_reason"]) == "STOP" for row in control)
    total_wins = sum(Decimal(str(row["realized_gross_r"])) > 0 for row in control)
    third_stops = sum(str(row["exit_reason"]) == "STOP" for row in third)
    third_wins = sum(Decimal(str(row["realized_gross_r"])) > 0 for row in third)

    cells: list[dict[str, Any]] = []
    for (
        journey_feature,
        journey_value,
        preentry_feature,
        preentry_value,
    ), selected in members.items():
        blocked = tuple(selected)
        blocked_keys = {_join_key(row) for row in blocked}
        kept = tuple(row for row in control if _join_key(row) not in blocked_keys)
        stops = sum(str(row["exit_reason"]) == "STOP" for row in blocked)
        wins = sum(Decimal(str(row["realized_gross_r"])) > 0 for row in blocked)
        cells.append(
            {
                "journey_feature": journey_feature,
                "journey_value": journey_value,
                "preentry_feature": preentry_feature,
                "preentry_value": preentry_value,
                "third_slot_trades": len(blocked),
                "third_slot_cell_metrics": _metrics(blocked),
                "third_slot_stops": stops,
                "third_slot_wins": wins,
                "third_slot_stop_capture_rate": (
                    "0"
                    if third_stops == 0
                    else str(Decimal(stops) / Decimal(third_stops))
                ),
                "third_slot_winner_sacrifice_rate": (
                    "0"
                    if third_wins == 0
                    else str(Decimal(wins) / Decimal(third_wins))
                ),
                "global_stop_capture_rate": (
                    "0"
                    if total_stops == 0
                    else str(Decimal(stops) / Decimal(total_stops))
                ),
                "global_winner_sacrifice_rate": (
                    "0"
                    if total_wins == 0
                    else str(Decimal(wins) / Decimal(total_wins))
                ),
                "full_portfolio_if_abstained_trades": len(kept),
                "full_portfolio_if_abstained_metrics": _metrics(kept),
                "density_retention_if_abstained": str(
                    Decimal(len(kept)) / Decimal(len(control))
                ),
            }
        )

    ordered = sorted(
        cells,
        key=lambda row: (
            str(row["journey_feature"]),
            str(row["journey_value"]),
            str(row["preentry_feature"]),
            str(row["preentry_value"]),
        ),
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
        "third_slot_trades": len(third),
        "third_slot_metrics": _metrics(third),
        "third_slot_stops": third_stops,
        "journey_features": JOURNEY_FEATURES,
        "preentry_features": PREENTRY_FEATURES,
        "pairwise_cell_count": len(ordered),
        "cells": ordered,
        "pairwise_only_no_three_way_search": True,
        "all_features_known_by_entry": True,
        "current_candidate_outcome_used_to_create_cell": False,
        "current_candidate_outcome_used_for_post_cell_metrics": True,
        "automatic_cell_selection": False,
        "runtime_rule_selected": False,
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
        "next_phase": "FALSIFY_PAIRWISE_THIRD_SLOT_CELLS_FOR_INFORMATION_VALUE_ONLY",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-third-slot-cross-feature-atlas-2y-v1.json"
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
