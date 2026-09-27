"""Run Phase 19J causal normalized walk-forward validation.

The six Phase-19I candidate policies are already frozen. This runner consumes
only post-freeze decisions, performs no policy refit or ranking, and splits the
post-freeze interval into two outcome-agnostic time folds.

The combined post-freeze replay preserves path dependence across the entire
forward interval. Per-fold replays reset to the same frozen gross capital only
to test temporal stability.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
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
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)
from qore.infrastructure.cibo_ce2i_phase19_simple_policy import (
    PHASE19I_SIMPLE_POLICIES,
    Phase19SimpleCapitalPolicy,
    Phase19SimplePolicyReplay,
    replay_phase19_simple_policy,
)
from qore.infrastructure.cibo_ce2i_phase19_walk_forward import (
    Phase19WalkForwardFold,
    build_phase19j_walk_forward_folds,
    phase19j_survival_failures,
)

CONTRACT_ID = "CIBO_PHASE19C_STRUCTURAL_STOP_NCU_V1"


def _times(
    row: dict[str, Any],
) -> tuple[datetime, datetime, datetime]:
    return (
        datetime.fromisoformat(str(row["signal_at"])),
        datetime.fromisoformat(str(row["entry_at"])),
        datetime.fromisoformat(str(row["exit_at"])),
    )


def _bind_freeze(
    trade: Phase19NormalizedReplayTrade,
    *,
    frozen_at: datetime,
) -> Phase19NormalizedReplayTrade:
    source = trade.allocation
    if source.decision_at < frozen_at:
        raise ValueError("Phase 19J pre-freeze decision leaked into validation")
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=source.signal_fingerprint,
        trader_id=source.trader_id,
        decision_at=source.decision_at,
        risk_budget_ncu=source.risk_budget_ncu,
        allocation_priority=source.allocation_priority,
        policy_id=source.policy_id,
        evidence_id=source.evidence_id,
        train_cutoff_at=frozen_at,
        outcome_aware=False,
    )
    return Phase19NormalizedReplayTrade(
        opportunity=trade.opportunity,
        allocation=allocation,
        normalized_outcome_r=trade.normalized_outcome_r,
        outcome_evidence_id=trade.outcome_evidence_id,
    )


def _metrics(result: Phase19SimplePolicyReplay) -> dict[str, Any]:
    replay = result.replay
    counts = Counter(item.status.value for item in replay.decisions)
    return {
        "opportunities": len(replay.decisions),
        "accepted_opportunities": replay.accepted_opportunities,
        "rejected_opportunities": replay.rejected_opportunities,
        "decision_status_counts": dict(sorted(counts.items())),
        "ending_total_capital_ncu": str(result.total_ending_capital_ncu),
        "total_realized_delta_ncu": str(replay.total_realized_delta_ncu),
        "max_drawdown_ncu": str(replay.max_drawdown_ncu),
        "peak_reserved_risk_ncu": str(replay.peak_reserved_risk_ncu),
        "risk_capacity_minutes_ncu": str(
            replay.risk_capacity_minutes_ncu
        ),
        "capacity_breach_observed": replay.capacity_breach_observed,
    }


def _fold_trades(
    trades: tuple[Phase19NormalizedReplayTrade, ...],
    *,
    fold: Phase19WalkForwardFold,
) -> tuple[Phase19NormalizedReplayTrade, ...]:
    return tuple(
        item
        for item in trades
        if item.allocation.decision_at >= fold.validation_start_at
        and item.opportunity.exit_at <= fold.validation_end_at
    )


def _policy_result(
    *,
    policy: Phase19SimpleCapitalPolicy,
    contract: Phase19CapitalNumeraireContract,
    combined_trades: tuple[Phase19NormalizedReplayTrade, ...],
    folds: tuple[Phase19WalkForwardFold, ...],
) -> dict[str, Any]:
    combined = replay_phase19_simple_policy(
        policy=policy,
        contract=contract,
        trades=combined_trades,
    )
    fold_trade_sets = tuple(
        _fold_trades(combined_trades, fold=fold) for fold in folds
    )
    if any(not items for items in fold_trade_sets):
        raise ValueError("Phase 19J walk-forward fold has no opportunities")
    fold_results = tuple(
        replay_phase19_simple_policy(
            policy=policy,
            contract=contract,
            trades=items,
        )
        for items in fold_trade_sets
    )
    failures = phase19j_survival_failures(
        combined=combined,
        folds=fold_results,
    )
    return {
        "policy_id": policy.policy_id,
        "frozen_policy": {
            "gross_initial_capital_ncu": str(
                policy.gross_initial_capital_ncu
            ),
            "fixed_reserve_ncu": str(policy.fixed_reserve_ncu),
            "risk_budget_ncu": str(policy.risk_budget_ncu),
            "policy_refit_between_folds": False,
        },
        "combined_post_freeze": _metrics(combined),
        "folds": [
            {
                "fold_id": fold.fold_id,
                "validation_start_at": fold.validation_start_at.isoformat(),
                "validation_end_at": fold.validation_end_at.isoformat(),
                "metrics": _metrics(result),
            }
            for fold, result in zip(folds, fold_results, strict=True)
        ],
        "survives_phase19j": not failures,
        "survival_failures": list(failures),
    }


def validate(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19J source set drift")

    common_start = datetime.fromisoformat(EXPECTED_COMMON_START)
    frozen_at = datetime.fromisoformat(EXPECTED_SPLIT_AT)
    common_end = datetime.fromisoformat(EXPECTED_COMMON_END)
    folds = build_phase19j_walk_forward_folds(
        frozen_at=frozen_at,
        common_end=common_end,
    )

    parsed_validation: dict[
        TraderLineage,
        list[Phase19NormalizedReplayTrade],
    ] = {}
    training_rows = 0
    entry_based_validation_rows = 0
    causal_validation_rows = 0
    pre_freeze_decision_exclusions = 0

    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-19J source row-count drift"
            )

        common_rows: list[dict[str, Any]] = []
        causal_rows: list[dict[str, Any]] = []
        for row in rows:
            signal_at, entry_at, exit_at = _times(row)
            if entry_at < common_start or exit_at > common_end:
                continue
            common_rows.append(row)
            if exit_at <= frozen_at:
                training_rows += 1
            if entry_at >= frozen_at:
                entry_based_validation_rows += 1
                if signal_at < frozen_at:
                    pre_freeze_decision_exclusions += 1
            if signal_at >= frozen_at and exit_at <= common_end:
                causal_rows.append(row)
                causal_validation_rows += 1

        if len(common_rows) != EXPECTED_COMMON_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-19J common row-count drift"
            )
        parsed_validation[spec.trader_id] = [
            _bind_freeze(_parse_trade(row, spec=spec), frozen_at=frozen_at)
            for row in causal_rows
        ]

    if training_rows != EXPECTED_TRAINING_OPPORTUNITIES:
        raise ValueError("Phase 19J training row-count drift")
    if entry_based_validation_rows != EXPECTED_VALIDATION_OPPORTUNITIES:
        raise ValueError("Phase 19J entry-based validation row-count drift")
    if set(parsed_validation) != set(PHASE19_REQUIRED_TRADERS):
        raise ValueError("Phase 19J Trader population drift")

    combined_trades = tuple(
        item
        for trader in PHASE19_REQUIRED_TRADERS
        for item in parsed_validation[trader]
    )
    if len(combined_trades) != causal_validation_rows:
        raise ValueError("Phase 19J causal validation population drift")
    if not combined_trades:
        raise ValueError("Phase 19J causal validation population is empty")

    fold_trade_sets = tuple(
        _fold_trades(combined_trades, fold=fold) for fold in folds
    )
    midpoint_crossing = (
        len(combined_trades) - sum(len(items) for items in fold_trade_sets)
    )
    if midpoint_crossing < 0:
        raise ValueError("Phase 19J fold accounting drift")

    contract = Phase19CapitalNumeraireContract(contract_id=CONTRACT_ID)
    policy_results = [
        _policy_result(
            policy=policy,
            contract=contract,
            combined_trades=combined_trades,
            folds=folds,
        )
        for policy in PHASE19I_SIMPLE_POLICIES
    ]
    survivors = [
        item["policy_id"]
        for item in policy_results
        if item["survives_phase19j"]
    ]

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19.causal_walk_forward.v1",
        "identity": "CIBO_PHASE19J_CAUSAL_NORMALIZED_WFO_V1",
        "status": "POST_FREEZE_FORWARD_VALIDATION_COMPLETE",
        "common_window": {
            "start": common_start.isoformat(),
            "policy_frozen_at": frozen_at.isoformat(),
            "end": common_end.isoformat(),
        },
        "causal_population": {
            "training_rows_before_freeze": training_rows,
            "entry_based_validation_rows": entry_based_validation_rows,
            "causal_decision_validation_rows": causal_validation_rows,
            "pre_freeze_decision_exclusions": (
                pre_freeze_decision_exclusions
            ),
            "midpoint_crossing_excluded_from_fold_resets": midpoint_crossing,
            "combined_replay_includes_midpoint_crossing": True,
        },
        "fold_design": {
            "count": len(folds),
            "time_split_outcome_tuned": False,
            "policy_refit_between_folds": False,
            "per_fold_capital_reset_for_stability_measurement": True,
            "combined_post_freeze_replay_preserves_path_dependence": True,
            "folds": [
                {
                    "fold_id": fold.fold_id,
                    "history_cutoff_at": fold.history_cutoff_at.isoformat(),
                    "validation_start_at": (
                        fold.validation_start_at.isoformat()
                    ),
                    "validation_end_at": fold.validation_end_at.isoformat(),
                    "opportunities": len(items),
                }
                for fold, items in zip(folds, fold_trade_sets, strict=True)
            ],
        },
        "survival_rule": {
            "combined_realized_delta_positive": True,
            "each_fold_realized_delta_positive": True,
            "capacity_breach_forbidden": True,
            "insolvent_rejection_forbidden": True,
            "magnitude_threshold_tuned": False,
            "policy_ranking_performed": False,
        },
        "policies": policy_results,
        "surviving_policy_ids": survivors,
        "surviving_policy_count": len(survivors),
        "interpretation": {
            "phase19j_can_qualify_candidates": True,
            "phase19j_can_certify_final_policy": False,
            "validation_evidence_now_used_for_policy_qualification": True,
            "phase22_sealed_holdout_must_be_fresh": True,
            "advanced_optimizer_authorized": False,
        },
        "governance": {
            "historical_usd_claimed": False,
            "historical_provider_economics_claimed": False,
            "raw_cross_trader_r_aggregation": False,
            "future_outcomes_used_for_allocation": False,
            "policy_parameters_changed_after_freeze": False,
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
