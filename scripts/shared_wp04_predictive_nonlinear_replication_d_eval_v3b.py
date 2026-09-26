"""Independent TEMPORAL_REPLICATION_D evaluator for WP-04 V3B.

This evaluator never fits a representation or probe on replication data.
It rebuilds the exact frozen V3 temporal representation from consumed
R8/R6/R5 evidence, rehydrates the exact eight frozen V3B second-order probes,
verifies the HOLDOUT_E PASS binding and then evaluates the preregistered
TEMPORAL_REPLICATION_D window.

Replication gate is unchanged:
- pooled incremental information >= 100 bps;
- >= 4/8 targets positive.

A D PASS is evidence that the V3B representation/readout transfers across an
independent earlier temporal regime. It does not authorize LIVE, production,
real capital, merge, sizing, risk or execution.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shared_wp04_historical_representation_discovery import _prepare_partition
from shared_wp04_invariant_representation_v2 import PARTITIONS, _prepare_source_partition
from shared_wp04_predictive_representation_v3 import POLICY, _build_transitions

from qore.infrastructure.core_stack_v2.representation_predictive_nonlinear_probe_v3b import (
    BASIS_ID,
    PredictiveSecondOrderEvaluation,
    PredictiveSecondOrderProbe,
    evaluate_predictive_second_order_probe_prepared,
    prepare_second_order_design,
)
from qore.infrastructure.core_stack_v2.representation_predictive_probe_v3 import (
    predictive_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    fit_predictive_representation,
)

SCHEMA = "qore.shared.wp04.predictive_nonlinear_replication_d_v3b.v1"
IDENTITY = "QORE_SHARED_WP04_PREDICTIVE_REPLICATION_D_V3B_001"
REPLICATION_PARTITION = "replication_d"
REPLICATION_START = datetime.fromisoformat("2025-07-14T00:00:00+00:00")
REPLICATION_END_EXCLUSIVE = datetime.fromisoformat("2026-07-13T00:00:00+00:00")
MINIMUM_POOLED_INCREMENTAL_BPS = 100
MINIMUM_POSITIVE_TARGETS = 4


def _probe_from_payload(payload: dict[str, Any]) -> PredictiveSecondOrderProbe:
    return PredictiveSecondOrderProbe(
        fitted_at=datetime.fromisoformat(payload["fitted_at"]),
        calibration_partitions=tuple(payload["calibration_partitions"]),
        target_name=str(payload["target_name"]),
        representation_fingerprint=str(payload["representation_fingerprint"]),
        ontology_names=tuple(payload["ontology_names"]),
        concept_ids=tuple(payload["concept_ids"]),
        basis_id=str(payload["basis_id"]),
        baseline_coefficients_micros=tuple(payload["baseline_coefficients_micros"]),
        augmented_coefficients_micros=tuple(payload["augmented_coefficients_micros"]),
        probe_fingerprint=str(payload["probe_fingerprint"]),
        representation_training_future_only=bool(
            payload["representation_training_future_only"]
        ),
        runtime_future_market_used=bool(payload["runtime_future_market_used"]),
        holdout_used_for_fit=bool(payload["holdout_used_for_fit"]),
        identity_used=bool(payload["identity_used"]),
        knowledge_promotion_authority=bool(payload["knowledge_promotion_authority"]),
    )


def _summary(
    evaluations: list[PredictiveSecondOrderEvaluation],
) -> dict[str, Any]:
    if not evaluations:
        raise ValueError("V3B replication summary requires evaluations")
    total_weight = sum(item.sample_count for item in evaluations)
    baseline = sum(
        item.baseline_mse_micros * item.sample_count for item in evaluations
    ) / total_weight
    augmented = sum(
        item.augmented_mse_micros * item.sample_count for item in evaluations
    ) / total_weight
    incremental = (
        0
        if baseline <= 0
        else int(round((baseline - augmented) / baseline * 10_000))
    )
    positive = sum(item.incremental_information_bps > 0 for item in evaluations)
    passed = (
        incremental >= MINIMUM_POOLED_INCREMENTAL_BPS
        and positive >= MINIMUM_POSITIVE_TARGETS
    )
    return {
        "target_count": len(evaluations),
        "positive_target_count": positive,
        "minimum_positive_target_count": MINIMUM_POSITIVE_TARGETS,
        "pooled_baseline_mse_micros": int(round(baseline)),
        "pooled_augmented_mse_micros": int(round(augmented)),
        "pooled_incremental_information_bps": incremental,
        "minimum_pooled_incremental_bps": MINIMUM_POOLED_INCREMENTAL_BPS,
        "pass": passed,
        "targets": [
            {
                "target_name": item.target_name,
                "sample_count": item.sample_count,
                "baseline_mse_micros": item.baseline_mse_micros,
                "augmented_mse_micros": item.augmented_mse_micros,
                "incremental_information_bps": item.incremental_information_bps,
                "probe_fingerprint": item.probe_fingerprint,
                "holdout_refit": item.holdout_refit,
                "runtime_future_market_used": item.runtime_future_market_used,
                "identity_used": item.identity_used,
                "knowledge_promotion_authority": item.knowledge_promotion_authority,
            }
            for item in evaluations
        ],
    }


def run(
    *,
    freeze_path: Path,
    holdout_e_result_path: Path,
    consumed: dict[str, dict[str, Path]],
    replication: dict[str, Path],
) -> dict[str, Any]:
    freeze = json.loads(freeze_path.read_text())
    if freeze["status"] != "WP04_V3B_PROBE_FROZEN_FOR_ONE_SHOT_HOLDOUT":
        raise ValueError("V3B freeze artifact is not authorized for replication")
    if freeze["protocol_pass"] is not True:
        raise ValueError("V3B freeze protocol did not pass")
    if freeze["development_gate_pass"] is not True:
        raise ValueError("V3B development gate did not pass")
    if freeze["probe_frozen_for_holdout"] is not True:
        raise ValueError("V3B nonlinear probes are not frozen")
    if freeze["decoder"]["basis_id"] != BASIS_ID:
        raise ValueError("V3B frozen basis drift")
    if freeze["decoder"]["target_specific_representation_retune"] is not False:
        raise ValueError("target-specific representation retune is forbidden")
    if len(freeze["final_frozen_probes"]) != 8:
        raise ValueError("V3B freeze must contain eight probes")

    holdout_e = json.loads(holdout_e_result_path.read_text())
    if holdout_e["status"] != "WP04_V3B_HOLDOUT_E_PASS_REPLICATION_REQUIRED":
        raise ValueError("HOLDOUT_E result does not authorize replication")
    if holdout_e["protocol_pass"] is not True or holdout_e["holdout_e_pass"] is not True:
        raise ValueError("HOLDOUT_E PASS is required before replication")
    if holdout_e["replication_required"] is not True:
        raise ValueError("HOLDOUT_E must explicitly require replication")
    if holdout_e["evaluation"]["minimum_pooled_incremental_bps"] != 100:
        raise ValueError("HOLDOUT_E gate drift")
    if holdout_e["evaluation"]["minimum_positive_target_count"] != 4:
        raise ValueError("HOLDOUT_E positive-target gate drift")

    transitions = {}
    for partition in PARTITIONS:
        episodes, _source_range = _prepare_source_partition(
            partition=partition,
            evidence_paths=consumed[partition],
        )
        transitions[partition] = _build_transitions(episodes)

    fitted_at = max(
        item.future.as_of for rows in transitions.values() for item in rows
    )
    model = fit_predictive_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        transitions_by_partition=transitions,
        policy=POLICY,
    )
    representation_fingerprint = predictive_representation_fingerprint(model)
    if representation_fingerprint != freeze["representation"]["fingerprint"]:
        raise ValueError("frozen V3 representation fingerprint drift")
    if representation_fingerprint != holdout_e["representation_fingerprint"]:
        raise ValueError("HOLDOUT_E representation fingerprint drift")

    probes = {
        payload["target_name"]: _probe_from_payload(payload)
        for payload in freeze["final_frozen_probes"]
    }
    if len(probes) != 8:
        raise ValueError("V3B frozen probe target names must be unique")
    frozen_probe_fingerprints = {
        probe.probe_fingerprint for probe in probes.values()
    }
    if frozen_probe_fingerprints != set(holdout_e["probe_fingerprints"]):
        raise ValueError("HOLDOUT_E probe fingerprint drift")
    if any(probe.basis_id != BASIS_ID for probe in probes.values()):
        raise ValueError("V3B probe basis drift")
    if any(
        probe.representation_fingerprint != representation_fingerprint
        for probe in probes.values()
    ):
        raise ValueError("V3B probe representation fingerprint drift")
    if any(
        probe.calibration_partitions != ("r8", "r6", "r5")
        for probe in probes.values()
    ):
        raise ValueError("V3B probes must remain calibrated on consumed partitions")
    if any(probe.holdout_used_for_fit for probe in probes.values()):
        raise ValueError("replication cannot participate in V3B probe fit")

    episodes, targets, replication_range = _prepare_partition(
        partition=REPLICATION_PARTITION,
        evidence_paths=replication,
    )
    if not episodes:
        raise ValueError("REPLICATION_D contains no evaluation episodes")
    if min(item.as_of for item in episodes) < REPLICATION_START:
        raise ValueError("REPLICATION_D begins before preregistered boundary")
    if max(item.as_of for item in episodes) >= REPLICATION_END_EXCLUSIVE:
        raise ValueError("REPLICATION_D crosses preregistered source boundary")
    if set(targets) != set(probes):
        raise ValueError("REPLICATION_D target schema drift")
    targets = {
        target_name: tuple(
            item
            for item in rows
            if REPLICATION_START <= item.observed_at < REPLICATION_END_EXCLUSIVE
        )
        for target_name, rows in targets.items()
    }
    if any(not rows for rows in targets.values()):
        raise ValueError("REPLICATION_D has an empty target after boundary filtering")

    prepared = prepare_second_order_design(model=model, episodes=episodes)
    evaluations = [
        evaluate_predictive_second_order_probe_prepared(
            model=model,
            probe=probes[target_name],
            partition=REPLICATION_PARTITION,
            prepared=prepared,
            targets=targets[target_name],
        )
        for target_name in sorted(probes)
    ]
    summary = _summary(evaluations)

    evaluated_probe_fingerprints = {
        item.probe_fingerprint for item in evaluations
    }
    if frozen_probe_fingerprints != evaluated_probe_fingerprints:
        raise ValueError("REPLICATION_D V3B probe fingerprint drift")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP04_V3B_REPLICATION_D_PASS"
            if summary["pass"]
            else "WP04_V3B_REPLICATION_D_FALSIFIED"
        ),
        "protocol_pass": True,
        "replication_d_pass": summary["pass"],
        "holdout_e_pass_bound": True,
        "wp04_replication_gate_pass": summary["pass"],
        "wp04_exit_gate_pass": False,
        "representation_fingerprint": representation_fingerprint,
        "decoder": {
            "basis_id": BASIS_ID,
            "representation_changed_from_v3": False,
            "target_specific_representation_retune": False,
        },
        "probe_fingerprints": sorted(frozen_probe_fingerprints),
        "replication": {
            "partition": REPLICATION_PARTITION,
            "preregistered_start_inclusive": REPLICATION_START.isoformat(),
            "preregistered_end_exclusive": REPLICATION_END_EXCLUSIVE.isoformat(),
            "observed_source_min": min(item.as_of for item in episodes).isoformat(),
            "observed_source_max": max(item.as_of for item in episodes).isoformat(),
            "evaluation_range": replication_range,
            "episode_count": len(episodes),
        },
        "evaluation": summary,
        "governance": {
            "replication_window_frozen_before_holdout_e_acquisition": True,
            "holdout_e_pass_required_before_replication": True,
            "consumed_representation_refit_on_replication": False,
            "probe_refit_on_replication": False,
            "replication_used_for_threshold_selection": False,
            "threshold_retuning_on_replication": False,
            "runtime_future_market_used": False,
            "identity_shortcut_used": False,
            "trade_outcome_or_pnl_used_as_feature": False,
            "holdout_a_consumed_invalid": True,
            "holdout_c_consumed_invalid": True,
            "replication_b_remains_sealed": True,
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


def _paths(args: argparse.Namespace, prefix: str) -> dict[str, Path]:
    return {
        "NAS100": getattr(args, f"{prefix}_nas"),
        "SP500": getattr(args, f"{prefix}_sp"),
        "US30": getattr(args, f"{prefix}_us"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--holdout-e-result", type=Path, required=True)
    for partition in PARTITIONS:
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--replication-nas", type=Path, required=True)
    parser.add_argument("--replication-sp", type=Path, required=True)
    parser.add_argument("--replication-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        freeze_path=args.freeze,
        holdout_e_result_path=args.holdout_e_result,
        consumed={
            partition: _paths(args, partition)
            for partition in PARTITIONS
        },
        replication=_paths(args, "replication"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "replication_d_pass": payload["replication_d_pass"],
                "pooled_incremental_information_bps": payload["evaluation"][
                    "pooled_incremental_information_bps"
                ],
                "positive_target_count": payload["evaluation"][
                    "positive_target_count"
                ],
                "wp04_replication_gate_pass": payload[
                    "wp04_replication_gate_pass"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
