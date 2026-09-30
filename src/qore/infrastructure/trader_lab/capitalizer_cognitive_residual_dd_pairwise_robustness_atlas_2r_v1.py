"""Pairwise robust residual-DD falsification for true-2R Capitalizer.

This is the narrow follow-up to the single-cell Residual DD Robustness Atlas.
Only two-way intersections of causal decision-time features are allowed.

Search controls:
- cell membership is constructed before outcomes are attached;
- only cells touching the common residual DD episode are evaluated;
- minimum global support and minimum common-residual coverage are fixed up front;
- every candidate must be tested across all six outcome-blind collision policies;
- no three-way search, ranking promotion, or runtime rule selection is allowed.

The purpose is to determine whether the residual 2R drawdown can be explained by
a compact causal interaction without destroying density.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2r_v1 as stoprisk_2r,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_residual_dd_robustness_atlas_2r_v1 as residual_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_simultaneous_factor_collision_atlas_2r_v1 as collision_2r,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_simultaneous_factor_collision_atlas_2y_v1 as collision_v1,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_RESIDUAL_DD_PAIRWISE_ROBUSTNESS_ATLAS_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_CROSS_RUN_ID = 36083458303
SOURCE_CROSS_SHA = "dbbef8abd9a75ab08da577dcf2e390e755b2f1fe"
SOURCE_COLLISION_RUN_ID = 36083729816
SOURCE_COLLISION_SHA = "4bf7c7a50f52653096bf75f984e39774d3c5dc36"
SOURCE_RESIDUAL_RUN_ID = 36084077143
SOURCE_RESIDUAL_SHA = "802adc13ae3b5f48f89b1f273bfd4fd89d2fe770"

MIN_GLOBAL_SUPPORT = 5
MIN_COMMON_RESIDUAL_COVERAGE = 2
MIN_DENSITY = Decimal("0.95")
DD_CEILING = Decimal("6")


def _load_residual_report(root: Path) -> dict[str, Any]:
    paths = sorted(
        root.rglob("capitalizer-cognitive-residual-dd-robustness-atlas-2r-v1.json")
    )
    if len(paths) != 1:
        raise ValueError("pairwise atlas requires one residual robustness artifact")
    report = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != residual_v1.IDENTITY:
        raise ValueError("unexpected residual robustness identity")
    if report.get("runtime_rule_selected") is not False:
        raise ValueError("pairwise atlas requires no selected runtime rule")
    return report


def _feature_map(row: dict[str, Any]) -> dict[str, str]:
    result = dict(residual_v1._causal_cells(row))
    if len(result) != len(residual_v1._causal_cells(row)):
        raise ValueError("pairwise feature map contains duplicate names")
    return result


def build_report(
    rebase_root: Path,
    cross_root: Path,
    collision_root: Path,
    residual_root: Path,
) -> dict[str, Any]:
    rebase_report, rows = collision_2r._load_rebase(rebase_root)
    cross_reference = collision_2r._load_cross_reference(cross_root)
    collision_report = residual_v1._load_collision_report(collision_root)
    residual_report = _load_residual_report(residual_root)
    control = tuple(collision_2r._trade(row) for row in rows)
    row_by_key = {residual_v1._join_key(row): row for row in rows}
    if len(row_by_key) != len(rows):
        raise ValueError("pairwise atlas rebase identity not unique")

    _, clusters, policy_drops = residual_v1._policy_base_drops(
        rows=rows,
        control=control,
        cross_reference=cross_reference,
    )
    episodes: dict[str, frozenset[tuple[str, str]]] = {}
    for policy, drop in policy_drops.items():
        kept = collision_2r._apply_drop(control, drop)
        episodes[policy] = residual_v1._episode_keys(kept)
    common_residual = frozenset(
        set.intersection(*(set(keys) for keys in episodes.values()))
    )
    if len(common_residual) != int(
        residual_report["common_residual_episode_trades"]
    ):
        raise ValueError("pairwise atlas residual episode drifted")

    features_by_key = {
        key: _feature_map(row) for key, row in row_by_key.items()
    }
    feature_names = tuple(sorted(next(iter(features_by_key.values())).keys()))
    if any(
        tuple(sorted(feature_map.keys())) != feature_names
        for feature_map in features_by_key.values()
    ):
        raise ValueError("pairwise causal feature contract drifted")

    pair_members: dict[
        tuple[str, str, str, str],
        set[tuple[str, str]],
    ] = defaultdict(set)
    residual_members: dict[
        tuple[str, str, str, str],
        set[tuple[str, str]],
    ] = defaultdict(set)

    for key, feature_map in features_by_key.items():
        for left, right in itertools.combinations(feature_names, 2):
            cell = (
                left,
                feature_map[left],
                right,
                feature_map[right],
            )
            pair_members[cell].add(key)
            if key in common_residual:
                residual_members[cell].add(key)

    candidate_cells = tuple(
        cell
        for cell, members in pair_members.items()
        if len(members) >= MIN_GLOBAL_SUPPORT
        and len(residual_members.get(cell, set()))
        >= MIN_COMMON_RESIDUAL_COVERAGE
    )

    total_stops = sum(str(row["exit_reason"]) == "STOP" for row in control)
    total_wins = sum(
        Decimal(str(row["realized_gross_r"])) > 0 for row in control
    )

    cells: list[dict[str, Any]] = []
    for cell in sorted(candidate_cells):
        left, left_value, right, right_value = cell
        extra_drop = frozenset(pair_members[cell])
        residual_coverage = residual_members[cell]
        blocked = tuple(
            row for row in control if residual_v1._join_key(row) in extra_drop
        )
        blocked_stops = sum(
            str(row["exit_reason"]) == "STOP" for row in blocked
        )
        blocked_wins = sum(
            Decimal(str(row["realized_gross_r"])) > 0 for row in blocked
        )

        per_policy: list[dict[str, Any]] = []
        for policy in collision_v1.POLICIES:
            combined_drop = frozenset((*policy_drops[policy], *extra_drop))
            kept = collision_2r._apply_drop(control, combined_drop)
            metrics = stoprisk_2r._metrics(kept)
            per_policy.append(
                {
                    "policy": policy,
                    "dropped_trades": len(combined_drop),
                    "metrics": metrics,
                    "density_retention": str(
                        Decimal(len(kept)) / Decimal(len(control))
                    ),
                }
            )

        worst_dd = max(
            Decimal(str(item["metrics"]["max_drawdown_r"]))
            for item in per_policy
        )
        finite_pfs = tuple(
            Decimal(str(item["metrics"]["profit_factor"]))
            for item in per_policy
            if item["metrics"]["profit_factor"] is not None
        )
        min_pf = min(finite_pfs) if finite_pfs else None
        min_total = min(
            Decimal(str(item["metrics"]["total_r"]))
            for item in per_policy
        )
        min_density = min(
            Decimal(str(item["density_retention"]))
            for item in per_policy
        )

        cells.append(
            {
                "left_feature": left,
                "left_value": left_value,
                "right_feature": right,
                "right_value": right_value,
                "common_residual_trades_covered": len(residual_coverage),
                "global_cell_trades": len(extra_drop),
                "global_cell_metrics": stoprisk_2r._metrics(blocked),
                "global_cell_stops": blocked_stops,
                "global_cell_wins": blocked_wins,
                "global_stop_capture_rate": (
                    "0"
                    if total_stops == 0
                    else str(Decimal(blocked_stops) / Decimal(total_stops))
                ),
                "global_winner_sacrifice_rate": (
                    "0"
                    if total_wins == 0
                    else str(Decimal(blocked_wins) / Decimal(total_wins))
                ),
                "policy_results": per_policy,
                "worst_case_max_drawdown_r": str(worst_dd),
                "worst_case_profit_factor": (
                    None if min_pf is None else str(min_pf)
                ),
                "worst_case_total_r": str(min_total),
                "worst_case_density_retention": str(min_density),
                "all_policies_at_or_below_6r_dd": worst_dd <= DD_CEILING,
                "all_policies_density_at_least_95pct": (
                    min_density >= MIN_DENSITY
                ),
            }
        )

    robust_under_6 = sum(
        bool(row["all_policies_at_or_below_6r_dd"]) for row in cells
    )
    robust_high_density = sum(
        bool(row["all_policies_at_or_below_6r_dd"])
        and bool(row["all_policies_density_at_least_95pct"])
        for row in cells
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_cross_run_id": SOURCE_CROSS_RUN_ID,
        "source_cross_sha": SOURCE_CROSS_SHA,
        "source_collision_run_id": SOURCE_COLLISION_RUN_ID,
        "source_collision_sha": SOURCE_COLLISION_SHA,
        "source_residual_run_id": SOURCE_RESIDUAL_RUN_ID,
        "source_residual_sha": SOURCE_RESIDUAL_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(control),
        "control_metrics": stoprisk_2r._metrics(control),
        "collision_cluster_count": len(clusters),
        "common_residual_episode_trades": len(common_residual),
        "feature_count": len(feature_names),
        "pair_feature_combinations": len(
            tuple(itertools.combinations(feature_names, 2))
        ),
        "minimum_global_support": MIN_GLOBAL_SUPPORT,
        "minimum_common_residual_coverage": MIN_COMMON_RESIDUAL_COVERAGE,
        "eligible_pairwise_cell_count": len(cells),
        "cells": cells,
        "robust_cells_at_or_below_6r_dd": robust_under_6,
        "robust_high_density_cells_at_or_below_6r_dd": robust_high_density,
        "pairwise_only_no_three_way_search": True,
        "all_features_known_by_entry": True,
        "current_outcome_used_to_create_cell": False,
        "current_outcome_used_for_post_cell_metrics": True,
        "all_six_collision_policies_required": True,
        "automatic_pair_selection": False,
        "runtime_rule_selected": False,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(control)
        ),
        "collision_control_reproduced": (
            int(collision_report["collision_cluster_count"]) == len(clusters)
        ),
        "residual_control_reproduced": (
            int(residual_report["control_trades"]) == len(control)
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
        "next_phase": "IF_ROBUST_HIGH_DENSITY_PAIR_EXISTS_FREEZE_ONE_FOR_FRESH_HOLDOUT",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-cognitive-residual-dd-pairwise-robustness-atlas-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("cross_root", type=Path)
    parser.add_argument("collision_root", type=Path)
    parser.add_argument("residual_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(
        args.rebase_root,
        args.cross_root,
        args.collision_root,
        args.residual_root,
    )
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
