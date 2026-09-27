"""WP-05 V11 mechanism-confirmation consumed-development experiment."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from shared_wp05_sequential_changepoint_v10 import (
    MINIMUM_BASELINE_TERMINALS,
    MINIMUM_EPISODES,
    MINIMUM_FALSE_REDUCTION_BPS,
    MINIMUM_TERMINAL_PRESERVATION_BPS,
    PARTITIONS,
    TARGET_CONTRACT,
    _partition_temporal_order_pass,
    _paths,
    _prepare_partition,
)

from qore.infrastructure.core_stack_v2.temporal_hierarchy_mechanism_confirmation_v11 import (
    V11MechanismConfirmationEvaluation,
    evaluate_v11_mechanism_confirmation,
    fit_v11_mechanism_confirmation_model,
    v11_model_fingerprint,
    v11_representation_fingerprint,
)

SCHEMA = "qore.shared.wp05.mechanism_confirmation_consumed.v11"
IDENTITY = "QORE_SHARED_WP05_SEQUENTIAL_MECHANISM_CONFIRMATION_V11_001"
REPRESENTATION = "TWO_OF_THREE_SEQUENTIAL_MECHANISM_CONFIRMATION_V11_001"


def _governance_payload() -> dict[str, object]:
    return {
        "preregistered_identity": IDENTITY,
        "target_v2_required": True,
        "checkpoints_minutes": [0, 3, 5, 10, 15],
        "t0_terminal_confirmation_allowed": False,
        "confirmation_mechanism_count_required": 2,
        "confirmation_mechanism_count_total": 3,
        "terminal_confirmation_absorbing": True,
        "r8_chronological_discovery_calibration_only": True,
        "r6_r5_unread_until_r8_model_frozen": True,
        "r8_r6_r5_temporally_ordered_nonoverlap_required": True,
        "r6_refit": False,
        "r5_refit": False,
        "r6_threshold_retuning": False,
        "r5_threshold_retuning": False,
        "runtime_future_market_used": False,
        "trade_pnl_used": False,
        "trader_identity_feature_used": False,
        "symbol_identity_feature_used": False,
        "setup_identity_feature_used": False,
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
    }


def _model_payload(model: Any) -> dict[str, Any]:
    return {
        "fit_partition": model.fit_partition,
        "checkpoints_minutes": list(model.checkpoints_minutes),
        "feature_names": list(model.feature_names),
        "feature_count": len(model.feature_names),
        "mechanism_feature_names": [
            [name, list(features)]
            for name, features in model.mechanism_feature_names
        ],
        "confirmation_threshold_micros": model.confirmation_threshold_micros,
        "source_comparator_threshold_micros": (
            model.source_comparator_threshold_micros
        ),
        "max_checkpoint_comparator_threshold_micros": (
            model.max_checkpoint_comparator_threshold_micros
        ),
        "calibration_confirmation_terminal_preservation_bps": (
            model.calibration_confirmation_terminal_preservation_bps
        ),
        "calibration_confirmation_false_reduction_bps": (
            model.calibration_confirmation_false_reduction_bps
        ),
        "calibration_source_terminal_preservation_bps": (
            model.calibration_source_terminal_preservation_bps
        ),
        "calibration_source_false_reduction_bps": (
            model.calibration_source_false_reduction_bps
        ),
        "calibration_max_terminal_preservation_bps": (
            model.calibration_max_terminal_preservation_bps
        ),
        "calibration_max_false_reduction_bps": (
            model.calibration_max_false_reduction_bps
        ),
        "calibration_gate_pass": model.calibration_gate_pass,
        "fit_count": model.fit_count,
        "fit_terminal_count": model.fit_terminal_count,
        "fit_nonterminal_count": model.fit_nonterminal_count,
        "calibration_count": model.calibration_count,
        "calibration_terminal_count": model.calibration_terminal_count,
        "calibration_nonterminal_count": model.calibration_nonterminal_count,
        "purged_discovery_count": model.purged_discovery_count,
        "discovery_observed_max": model.discovery_observed_max.isoformat(),
        "calibration_source_min": model.calibration_source_min.isoformat(),
        "densities": [asdict(item) for item in model.densities],
        "fingerprint_sha256": v11_model_fingerprint(model),
        "representation_fingerprint_sha256": v11_representation_fingerprint(),
        "representation": REPRESENTATION,
    }


def _evaluation_payload(
    evaluation: V11MechanismConfirmationEvaluation,
) -> dict[str, Any]:
    return asdict(evaluation)


def _r8_sample_gate(
    rows: tuple[Any, ...],
    partition_range: dict[str, int | str | None],
) -> bool:
    return (
        len(rows) >= MINIMUM_EPISODES
        and int(partition_range["complete_evidence_count"] or 0)
        >= MINIMUM_EPISODES
        and int(partition_range["terminal_event_count"] or 0)
        >= MINIMUM_BASELINE_TERMINALS
        and partition_range["target_contract"] == TARGET_CONTRACT
        and partition_range["fresh_holdout_opened"] == 0
        and int(partition_range["changed_target_count"] or 0) > 0
    )


def run(*, evidence: dict[str, dict[str, Path]]) -> dict[str, Any]:
    r8_rows, r8_range = _prepare_partition(
        partition="r8",
        evidence_paths=evidence["r8"],
    )
    ranges: dict[str, dict[str, int | str | None]] = {"r8": r8_range}
    if not _r8_sample_gate(r8_rows, r8_range):
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "representation": REPRESENTATION,
            "status": "WP05_V11_PROTOCOL_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "wp05_exit_gate_pass": False,
            "partition_ranges": ranges,
            "reason": "R8_SAMPLE_TARGET_GATE_FAILED",
            "governance": _governance_payload(),
        }

    model = fit_v11_mechanism_confirmation_model(
        fitted_at=max(item.observed_at for item in r8_rows),
        fit_partition="r8",
        episodes=r8_rows,
    )
    model_payload = _model_payload(model)
    r8_evaluation = evaluate_v11_mechanism_confirmation(
        model=model,
        partition="r8",
        episodes=r8_rows,
    )

    if not model.calibration_gate_pass:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "representation": REPRESENTATION,
            "status": "WP05_V11_MECHANISM_CONFIRMATION_FALSIFIED",
            "protocol_pass": True,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "wp05_exit_gate_pass": False,
            "partition_ranges": ranges,
            "model": model_payload,
            "partition_model_fingerprints": {
                "r8": model_payload["fingerprint_sha256"],
            },
            "evaluations": {"r8": _evaluation_payload(r8_evaluation)},
            "reason": "NO_LEGAL_R8_CONFIRMATION_CALIBRATION",
            "governance": _governance_payload(),
        }

    partitions = {"r8": r8_rows}
    for partition in ("r6", "r5"):
        rows, partition_range = _prepare_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        partitions[partition] = rows
        ranges[partition] = partition_range

    sample_gate = all(
        len(partitions[partition]) >= MINIMUM_EPISODES
        and int(ranges[partition]["complete_evidence_count"] or 0)
        >= MINIMUM_EPISODES
        for partition in PARTITIONS
    )
    terminal_gate = all(
        int(ranges[partition]["terminal_event_count"] or 0)
        >= MINIMUM_BASELINE_TERMINALS
        for partition in PARTITIONS
    )
    target_gate = all(
        ranges[partition]["target_contract"] == TARGET_CONTRACT
        and ranges[partition]["fresh_holdout_opened"] == 0
        and int(ranges[partition]["changed_target_count"] or 0) > 0
        for partition in PARTITIONS
    )
    partition_temporal_order_gate = _partition_temporal_order_pass(ranges)

    if not (
        sample_gate
        and terminal_gate
        and target_gate
        and partition_temporal_order_gate
    ):
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "representation": REPRESENTATION,
            "status": "WP05_V11_PROTOCOL_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "wp05_exit_gate_pass": False,
            "partition_temporal_order_gate": partition_temporal_order_gate,
            "partition_ranges": ranges,
            "model": model_payload,
            "reason": "SAMPLE_TARGET_OR_TEMPORAL_GATE_FAILED",
            "governance": _governance_payload(),
        }

    evaluations = {
        partition: evaluate_v11_mechanism_confirmation(
            model=model,
            partition=partition,
            episodes=partitions[partition],
        )
        for partition in PARTITIONS
    }
    development_gate_pass = all(
        evaluations[partition].v11_false_declaration_reduction_bps
        >= MINIMUM_FALSE_REDUCTION_BPS
        and evaluations[partition].v11_terminal_detection_preservation_bps
        >= MINIMUM_TERMINAL_PRESERVATION_BPS
        for partition in ("r6", "r5")
    )

    protocol_pass = (
        model.fit_partition == "r8"
        and model.calibration_gate_pass
        and model.calibration_confirmation_terminal_preservation_bps >= 9_800
        and model.discovery_observed_max < model.calibration_source_min
        and model.target_used_for_training_only
        and not model.runtime_future_market_used
        and not model.outcome_used_at_runtime
        and not model.trader_identity_used
        and not model.symbol_identity_used
        and not model.setup_identity_used
        and not model.pnl_used_at_runtime
        and not model.methodology_authority
        and not model.knowledge_promotion_authority
        and not model.sizing_authority
        and not model.risk_authority
        and not model.order_authority
        and not model.execution_authority
        and partition_temporal_order_gate
    )
    fingerprint = model_payload["fingerprint_sha256"]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "target_contract": TARGET_CONTRACT,
        "representation": REPRESENTATION,
        "status": (
            "WP05_V11_MECHANISM_CONFIRMATION_FROZEN_FOR_FRESH_HOLDOUT"
            if protocol_pass and development_gate_pass
            else "WP05_V11_MECHANISM_CONFIRMATION_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "development_gate_pass": development_gate_pass,
        "fresh_holdout_opened": False,
        "wp05_exit_gate_pass": False,
        "partition_temporal_order_gate": partition_temporal_order_gate,
        "partition_ranges": ranges,
        "model": model_payload,
        "partition_model_fingerprints": {
            partition: fingerprint for partition in PARTITIONS
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
            "must_pass_partitions": ["r6", "r5"],
            "maximum_confirmation_latency_minutes": 15,
        },
        "governance": _governance_payload(),
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
                "model": payload.get("model", {}),
                "evaluations": payload.get("evaluations", {}),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
