"""WP-04 V2 consumed-target diagnostics and final probe freeze.

The invariant representation was selected using source-only R8/R6/R5 evidence.
This stage is allowed to inspect matured generic future-state labels because all
three partitions are already consumed development evidence.

Before opening any new one-shot holdout, the fixed V2 representation must show
that latent concepts add information beyond the existing ontology in
leave-one-partition-out consumed target diagnostics. These diagnostics are NOT
fresh holdouts because source-only geometry from every partition already
participated in V2 representation selection.

If and only if the preregistered development gate passes, final probes are fit
on all consumed target evidence and fingerprinted. No holdout is opened here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import TARGET_CONCEPTS
from shared_wp04_historical_representation_discovery import _prepare_partition
from shared_wp04_invariant_representation_v2 import (
    PARTITIONS,
    POLICY,
    _prepare_source_partition,
)

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationEpisode,
)
from qore.infrastructure.core_stack_v2.representation_discovery_evaluation import (
    RepresentationEvaluationTarget,
)
from qore.infrastructure.core_stack_v2.representation_invariance_probe_v2 import (
    InvariantIncrementalEvaluation,
    evaluate_invariant_incremental_probe,
    fit_invariant_incremental_probe,
    invariant_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_invariance_v2 import (
    fit_invariant_representation,
)

SCHEMA = "qore.shared.wp04.invariant_probe_freeze_v2.v1"
IDENTITY = "QORE_SHARED_WP04_INVARIANT_PROBE_FREEZE_V2_001"
MINIMUM_POOLED_INCREMENTAL_BPS = 0
MINIMUM_POSITIVE_TARGETS = (len(TARGET_CONCEPTS) + 1) // 2
RIDGE = 1.0


def _pooled_summary(
    evaluations: list[InvariantIncrementalEvaluation],
) -> dict[str, Any]:
    if not evaluations:
        raise ValueError("probe diagnostic summary requires evaluations")
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
    positive = sum(
        item.incremental_information_bps > 0
        for item in evaluations
    )
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
                "partition": item.partition,
                "target_name": item.target_name,
                "sample_count": item.sample_count,
                "baseline_mse_micros": item.baseline_mse_micros,
                "augmented_mse_micros": item.augmented_mse_micros,
                "incremental_information_bps": (
                    item.incremental_information_bps
                ),
                "probe_fingerprint": item.probe_fingerprint,
                "holdout_refit": item.holdout_refit,
                "identity_used": item.identity_used,
                "knowledge_promotion_authority": (
                    item.knowledge_promotion_authority
                ),
            }
            for item in evaluations
        ],
    }


def _concat_episodes(
    prepared: dict[str, tuple[RepresentationEpisode, ...]],
    partitions: tuple[str, ...],
) -> tuple[RepresentationEpisode, ...]:
    return tuple(
        episode
        for partition in partitions
        for episode in prepared[partition]
    )


def _concat_targets(
    targets: dict[
        str,
        dict[str, tuple[RepresentationEvaluationTarget, ...]],
    ],
    *,
    target_name: str,
    partitions: tuple[str, ...],
) -> tuple[RepresentationEvaluationTarget, ...]:
    return tuple(
        target
        for partition in partitions
        for target in targets[partition][target_name]
    )


def _probe_payload(probe: Any) -> dict[str, Any]:
    return {
        "target_name": probe.target_name,
        "calibration_partitions": list(probe.calibration_partitions),
        "representation_fingerprint": probe.representation_fingerprint,
        "probe_fingerprint": probe.probe_fingerprint,
        "ontology_names": list(probe.ontology_names),
        "concept_ids": list(probe.concept_ids),
        "baseline_coefficients_micros": list(
            probe.baseline_coefficients_micros
        ),
        "augmented_coefficients_micros": list(
            probe.augmented_coefficients_micros
        ),
        "representation_target_blind": probe.representation_target_blind,
        "holdout_used_for_fit": probe.holdout_used_for_fit,
        "identity_used": probe.identity_used,
        "knowledge_promotion_authority": (
            probe.knowledge_promotion_authority
        ),
    }


def run(
    *,
    evidence: dict[str, dict[str, Path]],
) -> dict[str, Any]:
    source_partitions: dict[str, tuple[RepresentationEpisode, ...]] = {}
    source_ranges: dict[str, dict[str, str | None]] = {}
    for partition in PARTITIONS:
        episodes, source_range = _prepare_source_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        source_partitions[partition] = episodes
        source_ranges[partition] = source_range

    fitted_at = max(
        item.as_of
        for rows in source_partitions.values()
        for item in rows
    )
    model = fit_invariant_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        episodes_by_partition=source_partitions,
        policy=POLICY,
    )
    if not model.concepts:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP04_V2_NO_INVARIANT_CONCEPTS_FOR_PROBE",
            "protocol_pass": False,
            "probe_frozen_for_holdout": False,
            "fresh_holdout_opened": False,
        }

    evaluation_episodes: dict[
        str,
        tuple[RepresentationEpisode, ...],
    ] = {}
    evaluation_targets: dict[
        str,
        dict[str, tuple[RepresentationEvaluationTarget, ...]],
    ] = {}
    evaluation_ranges: dict[str, dict[str, str | None]] = {}
    for partition in PARTITIONS:
        episodes, targets, ranges = _prepare_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        evaluation_episodes[partition] = episodes
        evaluation_targets[partition] = targets
        evaluation_ranges[partition] = ranges

    representation_fingerprint = invariant_representation_fingerprint(model)
    leave_one_out: dict[str, dict[str, Any]] = {}

    for held in PARTITIONS:
        calibration = tuple(
            partition
            for partition in PARTITIONS
            if partition != held
        )
        calibration_episodes = _concat_episodes(
            evaluation_episodes,
            calibration,
        )
        evaluations: list[InvariantIncrementalEvaluation] = []
        for target_name in sorted(evaluation_targets[held]):
            calibration_targets = _concat_targets(
                evaluation_targets,
                target_name=target_name,
                partitions=calibration,
            )
            probe = fit_invariant_incremental_probe(
                model=model,
                fitted_at=max(
                    item.observed_at
                    for item in calibration_targets
                ),
                calibration_partitions=calibration,
                target_name=target_name,
                episodes=calibration_episodes,
                targets=calibration_targets,
                ridge=RIDGE,
            )
            evaluations.append(
                evaluate_invariant_incremental_probe(
                    model=model,
                    probe=probe,
                    partition=held,
                    episodes=evaluation_episodes[held],
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
        all_episodes = _concat_episodes(
            evaluation_episodes,
            PARTITIONS,
        )
        for target_name in sorted(evaluation_targets["r8"]):
            all_targets = _concat_targets(
                evaluation_targets,
                target_name=target_name,
                partitions=PARTITIONS,
            )
            probe = fit_invariant_incremental_probe(
                model=model,
                fitted_at=max(
                    item.observed_at
                    for item in all_targets
                ),
                calibration_partitions=PARTITIONS,
                target_name=target_name,
                episodes=all_episodes,
                targets=all_targets,
                ridge=RIDGE,
            )
            final_probes.append(_probe_payload(probe))

    protocol_pass = (
        representation_fingerprint
        and len(representation_fingerprint) == 64
        and model.target_used is False
        and model.future_market_used is False
        and model.outcome_used is False
        and model.pnl_used is False
        and model.trader_identity_used is False
        and model.symbol_identity_used is False
        and model.partition_identity_as_feature_used is False
        and model.knowledge_promotion_authority is False
        and model.methodology_authority is False
        and model.sizing_authority is False
        and model.risk_authority is False
        and model.order_authority is False
        and model.execution_authority is False
        and all(
            target["holdout_refit"] is False
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
        and len(
            {
                item["probe_fingerprint"]
                for item in final_probes
            }
        )
        == len(final_probes)
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP04_V2_PROBE_FROZEN_FOR_ONE_SHOT_HOLDOUT"
            if probe_frozen
            else "WP04_V2_TARGET_DIAGNOSTIC_FALSIFIED_BEFORE_HOLDOUT"
        ),
        "protocol_pass": bool(protocol_pass),
        "development_gate_pass": development_gate_pass,
        "probe_frozen_for_holdout": probe_frozen,
        "exit_gate_pass": False,
        "representation": {
            "fingerprint": representation_fingerprint,
            "candidate_count": model.candidate_count,
            "selected_concept_count": len(model.concepts),
            "concept_ids": [
                item.concept_id
                for item in model.concepts
            ],
            "evidence_cutoff_at": model.evidence_cutoff_at.isoformat(),
        },
        "source_ranges": source_ranges,
        "target_ranges": evaluation_ranges,
        "leave_one_partition_out_consumed_diagnostics": leave_one_out,
        "final_frozen_probes": final_probes,
        "frozen_probe_policy": {
            "ridge": RIDGE,
            "minimum_pooled_incremental_bps": (
                MINIMUM_POOLED_INCREMENTAL_BPS
            ),
            "minimum_positive_targets": MINIMUM_POSITIVE_TARGETS,
            "target_count": len(TARGET_CONCEPTS),
        },
        "governance": {
            "representation_source_invariance_frozen_before_targets": True,
            "r8_r6_r5_are_consumed_development": True,
            "leave_one_out_is_not_fresh_holdout": True,
            "future_labels_used_only_for_consumed_probe_development": True,
            "current_runtime_future_input_used": False,
            "trade_outcome_or_pnl_used": False,
            "identity_shortcut_used": False,
            "fresh_holdout_opened": False,
            "fresh_holdout_must_not_refit_representation": True,
            "fresh_holdout_must_not_refit_probe": True,
            "final_wp04_gate_minimum_incremental_bps_unchanged": 100,
            "final_wp04_gate_minimum_positive_targets_unchanged": (
                MINIMUM_POSITIVE_TARGETS
            ),
            "global_qore_validation_still_required": True,
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


def _partition_paths(
    args: argparse.Namespace,
    partition: str,
) -> dict[str, Path]:
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
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_pass": payload["protocol_pass"],
                "development_gate_pass": payload[
                    "development_gate_pass"
                ],
                "probe_frozen_for_holdout": payload[
                    "probe_frozen_for_holdout"
                ],
                "r8_incremental_bps": payload[
                    "leave_one_partition_out_consumed_diagnostics"
                ]["r8"]["pooled_incremental_information_bps"],
                "r6_incremental_bps": payload[
                    "leave_one_partition_out_consumed_diagnostics"
                ]["r6"]["pooled_incremental_information_bps"],
                "r5_incremental_bps": payload[
                    "leave_one_partition_out_consumed_diagnostics"
                ]["r5"]["pooled_incremental_information_bps"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
