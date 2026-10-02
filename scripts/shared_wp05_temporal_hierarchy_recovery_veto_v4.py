"""WP-05 V4 consumed-development terminal-safe recovery veto falsification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shared_wp05_temporal_hierarchy_absorption_v3 import (
    PARTITIONS,
    SCALE_HORIZONS,
    TRAJECTORY_OFFSETS_MINUTES,
    _paths,
    _prepare_partition,
)
from shared_wp05_temporal_hierarchy_v1 import (
    MINIMUM_BASELINE_TERMINALS,
    MINIMUM_EPISODES,
    MINIMUM_FALSE_REDUCTION_BPS,
    MINIMUM_TERMINAL_PRESERVATION_BPS,
)

from qore.infrastructure.core_stack_v2.temporal_hierarchy_recovery_veto_v4 import (
    TemporalHierarchyRecoveryVetoEvaluation,
    evaluate_temporal_hierarchy_recovery_veto,
    fit_temporal_hierarchy_recovery_veto_model,
)

SCHEMA = "qore.shared.wp05.temporal_hierarchy_recovery_veto_consumed_v4"
IDENTITY = "QORE_SHARED_WP05_TEMPORAL_HIERARCHY_RECOVERY_VETO_V4_001"


def _evaluation_payload(
    evaluation: TemporalHierarchyRecoveryVetoEvaluation,
) -> dict[str, int | str]:
    return {
        "partition": evaluation.partition,
        "sample_count": evaluation.sample_count,
        "baseline_declaration_count": evaluation.baseline_declaration_count,
        "baseline_terminal_count": evaluation.baseline_terminal_count,
        "baseline_false_declaration_count": (
            evaluation.baseline_false_declaration_count
        ),
        "hierarchy_declaration_count": evaluation.hierarchy_declaration_count,
        "hierarchy_terminal_count": evaluation.hierarchy_terminal_count,
        "hierarchy_false_declaration_count": (
            evaluation.hierarchy_false_declaration_count
        ),
        "hierarchy_missed_terminal_count": (
            evaluation.hierarchy_missed_terminal_count
        ),
        "false_declaration_reduction_bps": (
            evaluation.false_declaration_reduction_bps
        ),
        "terminal_detection_preservation_bps": (
            evaluation.terminal_detection_preservation_bps
        ),
    }


def run(*, evidence: dict[str, dict[str, Path]]) -> dict[str, Any]:
    partitions = {}
    ranges = {}
    for partition in PARTITIONS:
        rows, partition_range = _prepare_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        partitions[partition] = rows
        ranges[partition] = partition_range

    sample_gate = all(
        len(partitions[partition]) >= MINIMUM_EPISODES
        for partition in PARTITIONS
    )
    if not sample_gate:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP05_V4_SAMPLE_GATE_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "partition_ranges": ranges,
        }

    fitted_at = max(item.observed_at for item in partitions["r8"])
    model = fit_temporal_hierarchy_recovery_veto_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=partitions["r8"],
    )
    evaluations = {
        partition: evaluate_temporal_hierarchy_recovery_veto(
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
        and model.fit_partition == "r8"
        and model.calibration_terminal_preservation_bps >= 9_700
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
            "WP05_V4_RECOVERY_VETO_FROZEN_FOR_FRESH_HOLDOUT"
            if protocol_pass and development_gate_pass
            else "WP05_V4_RECOVERY_VETO_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "development_gate_pass": development_gate_pass,
        "fresh_holdout_opened": False,
        "wp05_exit_gate_pass": False,
        "partition_ranges": ranges,
        "trajectory_offsets_minutes": list(TRAJECTORY_OFFSETS_MINUTES),
        "scale_horizons_m1_bars": {
            scale.value: horizon for scale, horizon in SCALE_HORIZONS
        },
        "model": {
            "fit_partition": model.fit_partition,
            "fitted_at": model.fitted_at.isoformat(),
            "decision_architecture": "TERMINAL_SAFE_RECOVERY_VETO",
            "selected_level": model.selected_level,
            "minimum_cell_support": model.minimum_cell_support,
            "maximum_terminal_contamination_bps": (
                model.maximum_terminal_contamination_bps
            ),
            "calibration_false_reduction_bps": (
                model.calibration_false_reduction_bps
            ),
            "calibration_terminal_preservation_bps": (
                model.calibration_terminal_preservation_bps
            ),
            "fit_opposition_count": model.fit_opposition_count,
            "fit_terminal_count": model.fit_terminal_count,
            "motif_cell_count": len(model.motif_cells),
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
            "v1_gate_unchanged": True,
            "r8_fit_only": True,
            "r8_internal_chronological_calibration": True,
            "r8_calibration_terminal_buffer_bps": 9_700,
            "r6_refit": False,
            "r5_refit": False,
            "r6_threshold_retuning": False,
            "r5_threshold_retuning": False,
            "trajectory_source_only": True,
            "default_action_preserves_structural_failure": True,
            "only_high_purity_recovery_motif_can_veto": True,
            "runtime_future_market_used": False,
            "trade_pnl_used": False,
            "trader_identity_feature_used": False,
            "symbol_identity_feature_used": False,
            "fresh_holdout_opened": False,
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
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_pass": payload["protocol_pass"],
                "development_gate_pass": payload["development_gate_pass"],
                "model": payload.get("model", {}),
                "evaluations": payload.get("evaluations", {}),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
