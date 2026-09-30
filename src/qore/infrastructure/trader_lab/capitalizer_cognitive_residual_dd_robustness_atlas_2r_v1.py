"""Robust residual-drawdown atlas for the true-2R Capitalizer path.

Consumes:
- the true-2R cognitive rebase;
- the frozen 2R third-slot Cross-Feature development report;
- the successful true-2R simultaneous factor-collision atlas.

The lab does not choose one collision tie policy. Instead, it reconstructs all
six deterministic outcome-blind policies, finds the max-drawdown episode under
each combined path, intersects those episodes, and tests one additional causal
state cell at a time across *all six* policies.

A cell is robust only if its counterfactual survives every collision policy.
Current outcomes are attached only after causal feature membership is frozen.
No cell is promoted to runtime enforcement.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2r_v1 as stoprisk_2r,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2y_v1 as stoprisk_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_simultaneous_factor_collision_atlas_2r_v1 as collision_2r,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_simultaneous_factor_collision_atlas_2y_v1 as collision_v1,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_RESIDUAL_DD_ROBUSTNESS_ATLAS_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_CROSS_RUN_ID = 36083458303
SOURCE_CROSS_SHA = "dbbef8abd9a75ab08da577dcf2e390e755b2f1fe"
SOURCE_COLLISION_RUN_ID = 36083729816
SOURCE_COLLISION_SHA = "4bf7c7a50f52653096bf75f984e39774d3c5dc36"

DD_CEILING = Decimal("6")
MIN_DENSITY = Decimal("0.95")


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _sign(value: Decimal) -> str:
    if value > 0:
        return "POSITIVE"
    if value < 0:
        return "NEGATIVE"
    return "ZERO"


def _count_bucket(value: int) -> str:
    if value <= 2:
        return str(value)
    return "3_PLUS"


def _causal_cells(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    base = list(stoprisk_v1._causal_cells(row))
    base.extend(
        (
            ("SESSION_SLOT_INDEX", str(int(row["prior_same_session_selected"]))),
            (
                "SESSION_SLOTS_REMAINING",
                str(int(row["session_slots_remaining_before"])),
            ),
            (
                "PRIOR_DAY_REALIZED_SIGN",
                _sign(Decimal(str(row["prior_realized_r_today"]))),
            ),
            (
                "PRIOR_CLOSED_TRADES_TODAY",
                _count_bucket(int(row["prior_closed_trades_today"])),
            ),
            (
                "ACTIVE_POSITION_COUNT",
                _count_bucket(int(row["baseline_active_positions"])),
            ),
            (
                "COMPLETED_PRIOR_SESSIONS",
                ">".join(str(item) for item in row["completed_prior_sessions"])
                or "NONE",
            ),
        )
    )
    result = tuple(base)
    names = [name for name, _ in result]
    if len(names) != len(set(names)):
        raise ValueError("residual atlas causal feature names must be unique")
    return result


def _episode_keys(
    rows: tuple[dict[str, Any], ...],
) -> frozenset[tuple[str, str]]:
    ordered = tuple(
        sorted(
            rows,
            key=lambda row: (
                collision_2r._aware(row["entry_at"]),
                str(row["symbol"]),
            ),
        )
    )
    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    peak_index = -1
    max_peak_index = -1
    trough_index = -1

    for index, row in enumerate(ordered):
        equity += Decimal(str(row["realized_gross_r"]))
        if equity > peak:
            peak = equity
            peak_index = index
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            max_peak_index = peak_index
            trough_index = index

    start = max_peak_index + 1
    if trough_index < 0 or start > trough_index:
        return frozenset()
    return frozenset(_join_key(row) for row in ordered[start : trough_index + 1])


def _load_collision_report(root: Path) -> dict[str, Any]:
    paths = sorted(
        root.rglob(
            "capitalizer-cognitive-simultaneous-factor-collision-atlas-2r-v1.json"
        )
    )
    if len(paths) != 1:
        raise ValueError("residual atlas requires one 2R collision artifact")
    report = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != collision_2r.IDENTITY:
        raise ValueError("unexpected 2R collision identity")
    if report.get("collision_policy_selected") is not False:
        raise ValueError("residual atlas requires unselected collision policies")
    if report.get("combined_rule_selected") is not False:
        raise ValueError("residual atlas requires unselected combined rule")
    return report


def _policy_base_drops(
    *,
    rows: tuple[dict[str, Any], ...],
    control: tuple[dict[str, Any], ...],
    cross_reference: dict[str, Any],
) -> tuple[
    frozenset[tuple[str, str]],
    tuple[collision_v1.CollisionCluster, ...],
    dict[str, frozenset[tuple[str, str]]],
]:
    third_slot = collision_2r._third_slot_drop_keys(rows, control)
    if len(third_slot) != int(cross_reference["third_slot_trades"]):
        raise ValueError("residual atlas third-slot reference mismatch")
    clusters = collision_2r._build_clusters(rows)
    policy_drops: dict[str, frozenset[tuple[str, str]]] = {}
    for policy in collision_v1.POLICIES:
        collision_drop = collision_2r._collision_drop_keys(
            clusters,
            policy=policy,
        )
        policy_drops[policy] = frozenset((*third_slot, *collision_drop))
    return third_slot, clusters, policy_drops


def build_report(
    rebase_root: Path,
    cross_root: Path,
    collision_root: Path,
) -> dict[str, Any]:
    rebase_report, rows = collision_2r._load_rebase(rebase_root)
    cross_reference = collision_2r._load_cross_reference(cross_root)
    collision_report = _load_collision_report(collision_root)
    control = tuple(collision_2r._trade(row) for row in rows)
    row_by_key = {_join_key(row): row for row in rows}
    if len(row_by_key) != len(rows):
        raise ValueError("residual atlas rebase identity not unique")

    third_slot, clusters, policy_drops = _policy_base_drops(
        rows=rows,
        control=control,
        cross_reference=cross_reference,
    )

    episodes: dict[str, frozenset[tuple[str, str]]] = {}
    base_policy_metrics: dict[str, dict[str, Any]] = {}
    for policy, drop in policy_drops.items():
        kept = collision_2r._apply_drop(control, drop)
        episodes[policy] = _episode_keys(kept)
        base_policy_metrics[policy] = stoprisk_2r._metrics(kept)

    common_residual = set.intersection(
        *(set(keys) for keys in episodes.values())
    )
    common_residual_keys = frozenset(common_residual)

    cell_members: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    global_members: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for key, row in row_by_key.items():
        for cell in _causal_cells(row):
            global_members[cell].add(key)
            if key in common_residual_keys:
                cell_members[cell].add(key)

    total_stops = sum(str(row["exit_reason"]) == "STOP" for row in control)
    total_wins = sum(
        Decimal(str(row["realized_gross_r"])) > 0 for row in control
    )

    cells: list[dict[str, Any]] = []
    for (feature, value), residual_keys in sorted(cell_members.items()):
        extra_drop = frozenset(global_members[(feature, value)])
        blocked = tuple(
            row for row in control if _join_key(row) in extra_drop
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
                "feature": feature,
                "value": value,
                "common_residual_trades_covered": len(residual_keys),
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
                "all_policies_density_at_least_95pct": min_density >= MIN_DENSITY,
            }
        )

    robust_under_6 = sum(
        bool(row["all_policies_at_or_below_6r_dd"]) for row in cells
    )
    robust_under_6_high_density = sum(
        bool(row["all_policies_at_or_below_6r_dd"])
        and bool(row["all_policies_density_at_least_95pct"])
        for row in cells
    )

    episode_summary = {
        policy: {
            "episode_trades": len(keys),
            "common_episode_trades": len(keys & common_residual_keys),
            "base_metrics": base_policy_metrics[policy],
        }
        for policy, keys in episodes.items()
    }

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_cross_run_id": SOURCE_CROSS_RUN_ID,
        "source_cross_sha": SOURCE_CROSS_SHA,
        "source_collision_run_id": SOURCE_COLLISION_RUN_ID,
        "source_collision_sha": SOURCE_COLLISION_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(control),
        "control_metrics": stoprisk_2r._metrics(control),
        "third_slot_reference_trades": len(third_slot),
        "collision_cluster_count": len(clusters),
        "policy_count": len(policy_drops),
        "policy_base_metrics": base_policy_metrics,
        "policy_episode_summary": episode_summary,
        "common_residual_episode_trades": len(common_residual_keys),
        "common_residual_keys_used_only_to_seed_causal_cells": True,
        "causal_cell_count": len(cells),
        "cells": cells,
        "robust_cells_at_or_below_6r_dd": robust_under_6,
        "robust_high_density_cells_at_or_below_6r_dd": (
            robust_under_6_high_density
        ),
        "all_features_known_by_entry": True,
        "current_outcome_used_to_create_cell": False,
        "current_outcome_used_for_post_cell_metrics": True,
        "all_six_collision_policies_required": True,
        "automatic_cell_selection": False,
        "runtime_rule_selected": False,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(control)
        ),
        "collision_control_reproduced": (
            int(collision_report["control_trades"]) == len(control)
            and int(collision_report["collision_cluster_count"]) == len(clusters)
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
        "next_phase": "REVIEW_ROBUST_RESIDUAL_CELLS_THEN_FRESH_HOLDOUT_ONLY",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-residual-dd-robustness-atlas-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("cross_root", type=Path)
    parser.add_argument("collision_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(
        args.rebase_root,
        args.cross_root,
        args.collision_root,
    )
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
