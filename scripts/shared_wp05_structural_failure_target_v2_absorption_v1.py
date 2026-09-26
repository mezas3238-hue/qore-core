"""WP-05 Target V2 + hierarchy-absorption consumed-development experiment.

The original WP-05 target was falsified by the target-semantics audit as
materially inconsistent with the higher-timeframe structural-failure question.
This experiment keeps V1-V4 immutable and relabels the already-consumed
R8/R6/R5 trajectories under the activated Target V2 contract.

R8 fits the semi-Markov hierarchy-front hazard model and threshold. R6/R5 are
consumed falsification partitions only. No fresh holdout is opened.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shared_wp05_structural_failure_target_v2 import (
    relabel_partition_with_structural_failure_v2,
)
from shared_wp05_temporal_hierarchy_absorption_v3 import (
    MINIMUM_BASELINE_TERMINALS,
    MINIMUM_EPISODES,
    MINIMUM_FALSE_REDUCTION_BPS,
    MINIMUM_TERMINAL_PRESERVATION_BPS,
    PARTITIONS,
    SCALE_HORIZONS,
    TRAJECTORY_OFFSETS_MINUTES,
    _evaluation_payload,
    _paths,
)

from qore.infrastructure.core_stack_v2.temporal_hierarchy_absorption_v3 import (
    evaluate_temporal_hierarchy_absorption,
    fit_temporal_hierarchy_absorption_model,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectoryTrainingEpisode,
)

SCHEMA = "qore.shared.wp05.structural_failure_target_v2_absorption_consumed.v1"
IDENTITY = "QORE_SHARED_WP05_STRUCTURAL_FAILURE_TARGET_V2_ABSORPTION_V1_001"
TARGET_CONTRACT = "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2"
TARGET_AUDIT_RUN_ID = 36259738096
TARGET_AUDIT_GIT_SHA = "d7b6830d957a6dee12959236b6cef42d3b162f96"


def run(*, evidence: dict[str, dict[str, Path]]) -> dict[str, Any]:
    partitions: dict[
        str,
        tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
    ] = {}
    ranges: dict[str, dict[str, str | int | None]] = {}

    for partition in PARTITIONS:
        episodes, partition_range = (
            relabel_partition_with_structural_failure_v2(
                partition=partition,
                evidence_paths=evidence[partition],
            )
        )
        partitions[partition] = episodes
        ranges[partition] = partition_range

    sample_gate = all(
        len(partitions[partition]) >= MINIMUM_EPISODES
        for partition in PARTITIONS
    )
    target_contract_gate = all(
        ranges[partition]["target_contract"] == TARGET_CONTRACT
        and ranges[partition]["target_runtime_allowed"] == 0
        and ranges[partition]["fresh_holdout_opened"] == 0
        for partition in PARTITIONS
    )
    if not sample_gate or not target_contract_gate:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP05_TARGET_V2_ABSORPTION_SAMPLE_OR_CONTRACT_GATE_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "partition_ranges": ranges,
        }

    fitted_at = max(item.observed_at for item in partitions["r8"])
    model = fit_temporal_hierarchy_absorption_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=partitions["r8"],
        minimum_training_recall_bps=MINIMUM_TERMINAL_PRESERVATION_BPS,
    )
    evaluations = {
        partition: evaluate_temporal_hierarchy_absorption(
            model=model,
            partition=partition,
            episodes=partitions[partition],
        )
        for partition in PARTITIONS
    }

    development_gate_pass = all(
        evaluations[partition].baseline_terminal_count
        >= MINIMUM_BASELINE_TERMINALS
        and evaluations[partition].false_declaration_reduction_bps
        >= MINIMUM_FALSE_REDUCTION_BPS
        and evaluations[partition].terminal_detection_preservation_bps
        >= MINIMUM_TERMINAL_PRESERVATION_BPS
        for partition in ("r6", "r5")
    )

    protocol_pass = (
        sample_gate
        and target_contract_gate
        and model.fit_partition == "r8"
        and model.target_used_for_training_only is True
        and model.runtime_future_market_used is False
        and model.outcome_used_at_runtime is False
        and model.trader_identity_used is False
        and model.symbol_identity_used is False
        and model.methodology_authority is False
        and model.knowledge_promotion_authority is False
        and model.sizing_authority is False
        and model.risk_authority is False
        and model.order_authority is False
        and model.execution_authority is False
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP05_TARGET_V2_ABSORPTION_V1_FROZEN_FOR_FRESH_HOLDOUT"
            if protocol_pass and development_gate_pass
            else "WP05_TARGET_V2_ABSORPTION_V1_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "development_gate_pass": development_gate_pass,
        "fresh_holdout_opened": False,
        "wp05_exit_gate_pass": False,
        "target_contract": {
            "identity": TARGET_CONTRACT,
            "activated": True,
            "activation_audit_run_id": TARGET_AUDIT_RUN_ID,
            "activation_audit_git_sha": TARGET_AUDIT_GIT_SHA,
            "prior_v1_v4_history_rewritten": False,
            "runtime_target_access": False,
        },
        "partition_ranges": ranges,
        "trajectory_offsets_minutes": list(TRAJECTORY_OFFSETS_MINUTES),
        "scale_horizons_m1_bars": {
            scale.value: horizon for scale, horizon in SCALE_HORIZONS
        },
        "model": {
            "fit_partition": model.fit_partition,
            "fitted_at": model.fitted_at.isoformat(),
            "representation": "SEMI_MARKOV_HIERARCHY_FRONT_TARGET_V2",
            "declaration_threshold_micros": model.declaration_threshold_micros,
            "minimum_training_recall_bps": model.minimum_training_recall_bps,
            "threshold_calibration_recall_bps": (
                model.threshold_calibration_recall_bps
            ),
            "fit_opposition_count": model.fit_opposition_count,
            "fit_terminal_count": model.fit_terminal_count,
            "minimum_cell_support": model.minimum_cell_support,
            "prior_strength": model.prior_strength,
            "hazard_cell_count": len(model.hazard_cells),
        },
        "evaluations": {
            partition: _evaluation_payload(evaluation)
            for partition, evaluation in evaluations.items()
        },
        "frozen_development_gate": {
            "minimum_false_declaration_reduction_bps": (
                MINIMUM_FALSE_REDUCTION_BPS
            ),
            "minimum_terminal_detection_preservation_bps": (
                MINIMUM_TERMINAL_PRESERVATION_BPS
            ),
            "minimum_baseline_terminal_count": MINIMUM_BASELINE_TERMINALS,
            "must_pass_partitions": ["r6", "r5"],
        },
        "governance": {
            "target_v2_activated_after_preregistered_audit": True,
            "v1_v4_old_proxy_history_preserved": True,
            "r8_fit_only": True,
            "r6_refit": False,
            "r5_refit": False,
            "r6_threshold_retuning": False,
            "r5_threshold_retuning": False,
            "trajectory_source_only": True,
            "future_target_used_for_training_or_evaluation_only": True,
            "runtime_future_market_used": False,
            "trade_pnl_used": False,
            "trader_identity_feature_used": False,
            "symbol_identity_feature_used": False,
            "fresh_holdout_opened": False,
            "fresh_holdout_required_before_wp05_exit": True,
            "knowledge_auto_promotion": False,
            "shared_methodology_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_authority": False,
            "shared_order_authority": False,
            "shared_execution_authority": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in PARTITIONS:
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        evidence={
            partition: _paths(args, partition)
            for partition in PARTITIONS
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_pass": payload["protocol_pass"],
                "development_gate_pass": payload["development_gate_pass"],
                "target_contract": payload.get("target_contract", {}),
                "evaluations": payload.get("evaluations", {}),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
