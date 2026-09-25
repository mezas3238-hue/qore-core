"""Pairwise third-slot cross-feature falsification on the true-2R rebase.

Intersects one true-2R Journey feature with one causal pre-entry feature for each
of the frozen 40 third-slot candidates. Current outcomes are attached only after
cell construction. Pairwise cells are diagnostic; no cell is selected/promoted.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2r_v1 as stoprisk_2r,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2y_v1 as stoprisk_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_third_slot_journey_atlas_2r_v1 as journey_2r,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_THIRD_SLOT_CROSS_FEATURE_ATLAS_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"

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


def _cell_map(cells: tuple[tuple[str, str], ...]) -> dict[str, str]:
    result = dict(cells)
    if len(result) != len(cells):
        raise ValueError("duplicate causal feature")
    return result


def build_report(root: Path) -> dict[str, Any]:
    rebase_report, rows = journey_2r._load_rebase(root)
    control = tuple(journey_2r._trade(row) for row in rows)
    rebase_by_key = {_join_key(row): row for row in rows}
    if len(rebase_by_key) != len(rows):
        raise ValueError("2R cross-feature rebase identity not unique")

    third = tuple(
        trade
        for trade in control
        if int(rebase_by_key[_join_key(trade)]["prior_same_session_selected"]) == 2
    )
    if len(third) != 40:
        raise ValueError("2R cross-feature requires frozen 40 third slots")

    members: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in third:
        row = rebase_by_key[_join_key(candidate)]
        journey_cells = _cell_map(
            journey_2r._causal_cells(
                candidate=candidate,
                rebase_row=row,
                control=control,
            )
        )
        preentry_cells = _cell_map(stoprisk_v1._causal_cells(row))
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
        kept = tuple(
            row for row in control if _join_key(row) not in blocked_keys
        )
        stops = sum(str(row["exit_reason"]) == "STOP" for row in blocked)
        wins = sum(Decimal(str(row["realized_gross_r"])) > 0 for row in blocked)
        cells.append(
            {
                "journey_feature": journey_feature,
                "journey_value": journey_value,
                "preentry_feature": preentry_feature,
                "preentry_value": preentry_value,
                "third_slot_trades": len(blocked),
                "third_slot_cell_metrics": stoprisk_2r._metrics(blocked),
                "third_slot_stops": stops,
                "third_slot_wins": wins,
                "third_slot_stop_capture_rate": str(
                    Decimal(stops) / Decimal(third_stops)
                ),
                "third_slot_winner_sacrifice_rate": str(
                    Decimal(wins) / Decimal(third_wins)
                ),
                "global_stop_capture_rate": str(
                    Decimal(stops) / Decimal(total_stops)
                ),
                "global_winner_sacrifice_rate": str(
                    Decimal(wins) / Decimal(total_wins)
                ),
                "full_portfolio_if_abstained_trades": len(kept),
                "full_portfolio_if_abstained_metrics": stoprisk_2r._metrics(kept),
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
    dd_ceiling = Decimal("6")
    cells_at_or_below = sum(
        Decimal(str(row["full_portfolio_if_abstained_metrics"]["max_drawdown_r"]))
        <= dd_ceiling
        for row in ordered
    )
    high_density_at_or_below = sum(
        Decimal(str(row["full_portfolio_if_abstained_metrics"]["max_drawdown_r"]))
        <= dd_ceiling
        and Decimal(str(row["density_retention_if_abstained"])) >= Decimal("0.95")
        for row in ordered
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(control),
        "control_metrics": stoprisk_2r._metrics(control),
        "third_slot_trades": len(third),
        "third_slot_metrics": stoprisk_2r._metrics(third),
        "journey_features": JOURNEY_FEATURES,
        "preentry_features": PREENTRY_FEATURES,
        "pairwise_cell_count": len(ordered),
        "cells": ordered,
        "counterfactual_cells_at_or_below_6r_dd": cells_at_or_below,
        "high_density_cells_at_or_below_6r_dd": high_density_at_or_below,
        "pairwise_only_no_three_way_search": True,
        "all_features_known_by_entry": True,
        "dynamic_state_from_true_2r_rebase": True,
        "current_candidate_outcome_used_to_create_cell": False,
        "current_candidate_outcome_used_for_post_cell_metrics": True,
        "automatic_cell_selection": False,
        "runtime_rule_selected": False,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(control)
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
        "next_phase": "BIND_TRUE_2R_OPPORTUNITY_COMPETITION_AND_RESIDUAL_DD_FORENSICS",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-third-slot-cross-feature-atlas-2r-v1.json"
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
