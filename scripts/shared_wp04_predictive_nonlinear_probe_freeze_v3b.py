"""WP-04 V3B consumed nonlinear-decoder falsification.

The exact V3 temporal representation is kept unchanged. This lab asks whether
its latent concepts add information beyond a symmetric second-order ontology
baseline when decoded nonlinearly.

All evidence is already-consumed R8/R6/R5 development evidence. No fresh
holdout is opened. If all three leave-one-partition-out gates pass, exact V3B
probe fingerprints are frozen for a later one-shot holdout.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import TARGET_CONCEPTS
from shared_wp04_historical_representation_discovery import _prepare_partition
from shared_wp04_invariant_representation_v2 import PARTITIONS, _prepare_source_partition
from shared_wp04_predictive_representation_v3 import POLICY, _build_transitions

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationEpisode,
)
from qore.infrastructure.core_stack_v2.representation_discovery_evaluation import (
    RepresentationEvaluationTarget,
)
from qore.infrastructure.core_stack_v2.representation_predictive_nonlinear_probe_v3b import (
    BASIS_ID,
    PredictiveSecondOrderEvaluation,
    combine_second_order_designs,
    evaluate_predictive_second_order_probe_prepared,
    fit_predictive_second_order_probe_prepared,
    prepare_second_order_design,
)
from qore.infrastructure.core_stack_v2.representation_predictive_probe_v3 import (
    predictive_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    fit_predictive_representation,
)

SCHEMA = "qore.shared.wp04.predictive_nonlinear_probe_freeze_v3b.v1"
IDENTITY = "QORE_SHARED_WP04_PREDICTIVE_NONLINEAR_PROBE_V3B_001"
MINIMUM_POOLED_INCREMENTAL_BPS = 0
MINIMUM_POSITIVE_TARGETS = (len(TARGET_CONCEPTS) + 1) // 2
FINAL_HOLDOUT_MINIMUM_INCREMENTAL_BPS = 100
RIDGE = 1.0


def _concat_targets(
    targets: dict[str, dict[str, tuple[RepresentationEvaluationTarget, ...]]],
    *,
    target_name: str,
    partitions: tuple[str, ...],
) -> tuple[RepresentationEvaluationTarget, ...]:
    return tuple(
        target
        for partition in partitions
        for target in targets[partition][target_name]
    )


def _pooled_summary(
    evaluations: list[PredictiveSecondOrderEvaluation],
) -> dict[str, Any]:
    if not evaluations:
        raise ValueError("V3B summary requires evaluations")
    total_weight = sum(item.sample_count for item in evaluations)
    baseline = sum(
        item.baseline_mse_micros * item.sample_count
        for item in evaluations
    ) / total_weight
    augmented = sum(
        item.augmented_mse_micros * item.sample_count
        for item in evaluations
    ) / total_weight
    incremental = (
        0
        if baseline <= 0
        else int(round((baseline - augmented) / baseline * 10_000))
    )
    positive = sum(item.incremental_information_bps > 0 for item in evaluations)
    return {
        "target_count": len(evaluations),
        "positive_target_count": positive,
        "minimum_positive_target_count": MINIMUM_POSITIVE_TARGETS,
        "pooled_baseline_mse_micros": int(round(baseline)),
        "pooled_augmented_mse_micros": int(round(augmented)),
        "pooled_incremental_information_bps": incremental,
        "minimum_pooled_incremental_bps": MINIMUM_POOLED_INCREMENTAL_BPS,
        "pass": (
            incremental >= MINIMUM_POOLED_INCREMENTAL_BPS
            and positive >= MINIMUM_POSITIVE_TARGETS
        ),
        "targets": [
            {
                "partition": item.partition,
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


def _probe_payload(probe: Any) -> dict[str, Any]:
    return {
        "fitted_at": probe.fitted_at.isoformat(),
        "target_name": probe.target_name,
        "calibration_partitions": list(probe.calibration_partitions),
        "representation_fingerprint": probe.representation_fingerprint,
        "probe_fingerprint": probe.probe_fingerprint,
        "basis_id": probe.basis_id,
        "ontology_names": list(probe.ontology_names),
        "concept_ids": list(probe.concept_ids),
        "baseline_coefficients_micros": list(probe.baseline_coefficients_micros),
        "augmented_coefficients_micros": list(probe.augmented_coefficients_micros),
        "representation_training_future_only": (
            probe.representation_training_future_only
        ),
        "runtime_future_market_used": probe.runtime_future_market_used,
        "holdout_used_for_fit": probe.holdout_used_for_fit,
        "identity_used": probe.identity_used,
        "knowledge_promotion_authority": probe.knowledge_promotion_authority,
    }


def run(*, evidence: dict[str, dict[str, Path]]) -> dict[str, Any]:
    source_partitions: dict[str, tuple[RepresentationEpisode, ...]] = {}
    transitions = {}
    for partition in PARTITIONS:
        episodes, _source_range = _prepare_source_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        source_partitions[partition] = episodes
        transitions[partition] = _build_transitions(episodes)

    representation_fitted_at = max(
        item.future.as_of
        for rows in transitions.values()
        for item in rows
    )
    model = fit_predictive_representation(
        fitted_at=representation_fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        transitions_by_partition=transitions,
        policy=POLICY,
    )
    if not model.concepts:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP04_V3B_NO_TEMPORAL_CONCEPTS",
            "protocol_pass": False,
            "development_gate_pass": False,
            "probe_frozen_for_holdout": False,
            "fresh_holdout_opened": False,
        }

    evaluation_episodes: dict[str, tuple[RepresentationEpisode, ...]] = {}
    evaluation_targets: dict[
        str,
        dict[str, tuple[RepresentationEvaluationTarget, ...]],
    ] = {}
    for partition in PARTITIONS:
        episodes, targets, _ranges = _prepare_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        evaluation_episodes[partition] = episodes
        evaluation_targets[partition] = targets

    prepared = {
        partition: prepare_second_order_design(
            model=model,
            episodes=evaluation_episodes[partition],
        )
        for partition in PARTITIONS
    }

    representation_fingerprint = predictive_representation_fingerprint(model)
    leave_one_out: dict[str, dict[str, Any]] = {}

    for held in PARTITIONS:
        calibration = tuple(
            partition for partition in PARTITIONS if partition != held
        )
        calibration_design = combine_second_order_designs(
            [prepared[partition] for partition in calibration]
        )
        evaluations: list[PredictiveSecondOrderEvaluation] = []
        for target_name in sorted(evaluation_targets[held]):
            calibration_targets = _concat_targets(
                evaluation_targets,
                target_name=target_name,
                partitions=calibration,
            )
            probe = fit_predictive_second_order_probe_prepared(
                model=model,
                fitted_at=max(
                    item.observed_at for item in calibration_targets
                ),
                calibration_partitions=calibration,
                target_name=target_name,
                prepared=calibration_design,
                targets=calibration_targets,
                ridge=RIDGE,
            )
            evaluations.append(
                evaluate_predictive_second_order_probe_prepared(
                    model=model,
                    probe=probe,
                    partition=held,
                    prepared=prepared[held],
                    targets=evaluation_targets[held][target_name],
                )
            )
        leave_one_out[held] = _pooled_summary(evaluations)

    development_gate_pass = all(
        leave_one_out[partition]["pass"]
        for partition in PARTITIONS
    )

    final_probes: list[dict[str, Any]] = []
    if development_gate_pass:
        all_design = combine_second_order_designs(
            [prepared[partition] for partition in PARTITIONS]
        )
        for target_name in sorted(evaluation_targets["r8"]):
            all_targets = _concat_targets(
                evaluation_targets,
                target_name=target_name,
                partitions=PARTITIONS,
            )
            probe = fit_predictive_second_order_probe_prepared(
                model=model,
                fitted_at=max(item.observed_at for item in all_targets),
                calibration_partitions=PARTITIONS,
                target_name=target_name,
                prepared=all_design,
                targets=all_targets,
                ridge=RIDGE,
            )
            final_probes.append(_probe_payload(probe))

    protocol_pass = (
        len(representation_fingerprint) == 64
        and model.training_future_market_used is True
        and model.runtime_future_market_used is False
        and model.named_evaluation_target_used is False
        and model.outcome_used is False
        and model.pnl_used is False
        and model.trader_identity_used is False
        and model.symbol_identity_used is False
        and model.partition_identity_as_feature_used is False
        and all(
            target["holdout_refit"] is False
            and target["runtime_future_market_used"] is False
            and target["identity_used"] is False
            and target["knowledge_promotion_authority"] is False
            for summary in leave_one_out.values()
            for target in summary["targets"]
        )
    )
    probe_frozen = (
        protocol_pass
        and development_gate_pass
        and len(final_probes) == len(TARGET_CONCEPTS)
        and len({item["probe_fingerprint"] for item in final_probes})
        == len(final_probes)
        and all(item["basis_id"] == BASIS_ID for item in final_probes)
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP04_V3B_PROBE_FROZEN_FOR_ONE_SHOT_HOLDOUT"
            if probe_frozen
            else "WP04_V3B_NONLINEAR_DECODER_FALSIFIED_BEFORE_HOLDOUT"
        ),
        "protocol_pass": bool(protocol_pass),
        "development_gate_pass": development_gate_pass,
        "probe_frozen_for_holdout": probe_frozen,
        "exit_gate_pass": False,
        "fresh_holdout_opened": False,
        "representation": {
            "fingerprint": representation_fingerprint,
            "horizon_minutes": model.horizon_minutes,
            "selected_concept_count": len(model.concepts),
            "concept_ids": [item.concept_id for item in model.concepts],
        },
        "decoder": {
            "basis_id": BASIS_ID,
            "ridge": RIDGE,
            "baseline_capacity": (
                "INTERCEPT+ONTOLOGY_LINEAR+ONTOLOGY_SQUARES+ONTOLOGY_PAIRS"
            ),
            "augmented_additions": (
                "LATENT_LINEAR+LATENT_SQUARES+LATENT_PAIRS+ONTOLOGY_X_LATENT"
            ),
            "target_specific_representation_retune": False,
        },
        "leave_one_partition_out_consumed_diagnostics": leave_one_out,
        "final_frozen_probes": final_probes,
        "governance": {
            "r8_r6_r5_are_consumed_development": True,
            "representation_unchanged_from_v3": True,
            "decoder_capacity_falsification_only": True,
            "fresh_holdout_opened": False,
            "fresh_holdout_must_not_refit_representation": True,
            "fresh_holdout_must_not_refit_probe": True,
            "final_wp04_gate_minimum_incremental_bps_unchanged": (
                FINAL_HOLDOUT_MINIMUM_INCREMENTAL_BPS
            ),
            "final_wp04_gate_minimum_positive_targets_unchanged": (
                MINIMUM_POSITIVE_TARGETS
            ),
            "identity_shortcut_used": False,
            "trade_outcome_or_pnl_used": False,
            "runtime_future_market_used": False,
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


def _partition_paths(args: argparse.Namespace, partition: str) -> dict[str, Path]:
    return {
        "NAS100": getattr(args, f"{partition}_nas"),
        "SP500": getattr(args, f"{partition}_sp"),
        "US30": getattr(args, f"{partition}_us"),
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
            partition: _partition_paths(args, partition)
            for partition in PARTITIONS
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    diagnostics = payload.get(
        "leave_one_partition_out_consumed_diagnostics",
        {},
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_pass": payload["protocol_pass"],
                "development_gate_pass": payload.get(
                    "development_gate_pass",
                    False,
                ),
                "probe_frozen_for_holdout": payload.get(
                    "probe_frozen_for_holdout",
                    False,
                ),
                "r8_incremental_bps": diagnostics.get("r8", {}).get(
                    "pooled_incremental_information_bps"
                ),
                "r6_incremental_bps": diagnostics.get("r6", {}).get(
                    "pooled_incremental_information_bps"
                ),
                "r5_incremental_bps": diagnostics.get("r5", {}).get(
                    "pooled_incremental_information_bps"
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
