"""Run Phase 19I simple normalized-capital policies on TRAIN only.

The suite is frozen before empirical execution. It intentionally excludes
Trader-specific weights, overlap penalties, hypergraph penalties, dependence
thresholds, advanced optimizers and validation-driven tuning.

Validation rows are counted for split integrity but their outcomes are never
parsed into policy replay objects in this script.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
)
from cibo_phase19_normalized_capital_mechanics import _parse_trade
from cibo_phase19_temporal_stability_validation import (
    EXPECTED_SPLIT_AT,
    EXPECTED_TRAINING_OPPORTUNITIES,
    EXPECTED_VALIDATION_OPPORTUNITIES,
)

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)
from qore.infrastructure.cibo_ce2i_phase19_simple_policy import (
    PHASE19I_SIMPLE_POLICIES,
    Phase19SimpleCapitalPolicy,
    replay_phase19_simple_policy,
)

CONTRACT_ID = "CIBO_PHASE19C_STRUCTURAL_STOP_NCU_V1"


def _interval(row: dict[str, Any]) -> tuple[datetime, datetime]:
    return (
        datetime.fromisoformat(str(row["entry_at"])),
        datetime.fromisoformat(str(row["exit_at"])),
    )


def _policy_report(
    *,
    policy: Phase19SimpleCapitalPolicy,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
    contract: Phase19CapitalNumeraireContract,
) -> dict[str, Any]:
    result = replay_phase19_simple_policy(
        policy=policy,
        contract=contract,
        trades=trades,
    )
    replay = result.replay
    counts = Counter(item.status.value for item in replay.decisions)
    acceptance_rate = (
        Decimal(replay.accepted_opportunities) / Decimal(len(trades))
    )
    delta_per_drawdown = (
        replay.total_realized_delta_ncu / replay.max_drawdown_ncu
        if replay.max_drawdown_ncu > 0
        else None
    )
    return {
        "policy_id": policy.policy_id,
        "gross_initial_capital_ncu": str(policy.gross_initial_capital_ncu),
        "fixed_reserve_ncu": str(policy.fixed_reserve_ncu),
        "deployable_initial_capital_ncu": str(
            policy.deployable_initial_capital_ncu
        ),
        "risk_budget_ncu": str(policy.risk_budget_ncu),
        "accepted_opportunities": replay.accepted_opportunities,
        "rejected_opportunities": replay.rejected_opportunities,
        "decision_status_counts": dict(sorted(counts.items())),
        "acceptance_rate": str(acceptance_rate),
        "ending_deployable_capital_ncu": str(replay.ending_capital_ncu),
        "ending_total_capital_ncu": str(result.total_ending_capital_ncu),
        "total_realized_delta_ncu": str(replay.total_realized_delta_ncu),
        "max_drawdown_ncu": str(replay.max_drawdown_ncu),
        "peak_reserved_risk_ncu": str(replay.peak_reserved_risk_ncu),
        "risk_capacity_minutes_ncu": str(replay.risk_capacity_minutes_ncu),
        "realized_delta_per_max_drawdown_ncu": (
            str(delta_per_drawdown)
            if delta_per_drawdown is not None
            else None
        ),
        "capacity_breach_observed": replay.capacity_breach_observed,
    }


def validate(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19I source set drift")

    common_start = datetime.fromisoformat(EXPECTED_COMMON_START)
    split_at = datetime.fromisoformat(EXPECTED_SPLIT_AT)
    common_end = datetime.fromisoformat(EXPECTED_COMMON_END)

    training: dict[TraderLineage, list[Phase19NormalizedReplayTrade]] = {}
    validation_rows = 0
    crossing_rows = 0

    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-19I source row-count drift"
            )

        common_rows: list[dict[str, Any]] = []
        train_rows: list[dict[str, Any]] = []
        trader_validation_rows = 0
        trader_crossing_rows = 0
        for row in rows:
            entry_at, exit_at = _interval(row)
            if entry_at < common_start or exit_at > common_end:
                continue
            common_rows.append(row)
            if exit_at <= split_at:
                train_rows.append(row)
            elif entry_at >= split_at:
                trader_validation_rows += 1
            else:
                trader_crossing_rows += 1

        if len(common_rows) != EXPECTED_COMMON_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-19I common row-count drift"
            )
        validation_rows += trader_validation_rows
        crossing_rows += trader_crossing_rows
        training[spec.trader_id] = [
            _parse_trade(row, spec=spec) for row in train_rows
        ]

    if set(training) != set(PHASE19_REQUIRED_TRADERS):
        raise ValueError("Phase 19I Trader population drift")

    train_trades = tuple(
        item
        for trader in PHASE19_REQUIRED_TRADERS
        for item in training[trader]
    )
    if len(train_trades) != EXPECTED_TRAINING_OPPORTUNITIES:
        raise ValueError("Phase 19I training row-count drift")
    if validation_rows != EXPECTED_VALIDATION_OPPORTUNITIES:
        raise ValueError("Phase 19I validation row-count drift")
    if crossing_rows != 0:
        raise ValueError("Phase 19I unexpected split-crossing opportunity")

    contract = Phase19CapitalNumeraireContract(contract_id=CONTRACT_ID)
    policy_results = [
        _policy_report(
            policy=policy,
            trades=train_trades,
            contract=contract,
        )
        for policy in PHASE19I_SIMPLE_POLICIES
    ]

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19.simple_policy_baselines.v1",
        "identity": "CIBO_PHASE19I_SIMPLE_CAPITAL_POLICY_BASELINES_V1",
        "status": "TRAIN_ONLY_SIMPLE_BASELINES_MEASURED_NO_SELECTION",
        "training_window": {
            "start": common_start.isoformat(),
            "end": split_at.isoformat(),
            "opportunities": len(train_trades),
        },
        "validation_guard": {
            "rows_verified": validation_rows,
            "outcomes_used_for_policy_evaluation": False,
            "outcomes_used_for_policy_selection": False,
            "parameters_tuned_on_validation": False,
        },
        "design_basis": {
            "gross_initial_capital_ncu": "10",
            "gross_capital_source": (
                "predeclared Phase-19G loose-capacity reference"
            ),
            "risk_budgets_ncu": ["1", "0.75", "0.50", "0.25"],
            "risk_budget_grid_outcome_tuned": False,
            "reserve_ncu": ["0", "2"],
            "reserve_basis": (
                "2 NCU is the smallest predeclared Phase-19G scarcity scenario"
            ),
            "trader_specific_weights": False,
            "overlap_penalties": False,
            "dependence_thresholds": False,
            "hypergraph_penalties": False,
            "advanced_optimizer": False,
        },
        "policies": policy_results,
        "phase19j_candidate_policy_ids": [
            item.policy_id for item in PHASE19I_SIMPLE_POLICIES
        ],
        "selection": {
            "policy_selected": False,
            "ranking_frozen": False,
            "all_predeclared_policies_advance_to_phase19j": True,
            "reason": (
                "Phase 19I is baseline measurement; causal WFO performs "
                "forward comparison without validation mining"
            ),
        },
        "governance": {
            "research_only": True,
            "historical_usd_claimed": False,
            "historical_provider_economics_claimed": False,
            "raw_cross_trader_r_aggregation": False,
            "validation_outcomes_used": False,
            "allocator_policy_certified": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {key: getattr(args, key) for key in SOURCE_SPECS}
    print(json.dumps(validate(paths=paths, output_path=args.output), sort_keys=True))


if __name__ == "__main__":
    main()
