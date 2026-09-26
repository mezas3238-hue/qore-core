"""Pre-registered one-shot evaluator for WP-04 predictive representation V3.

This module cannot acquire market data. It only evaluates an already-opened
HOLDOUT_A evidence bundle against exact frozen representation/probe
fingerprints produced by the consumed V3 probe-freeze stage.

The representation is deterministically rebuilt from consumed R8/R6/R5
evidence and must fingerprint-match the freeze artifact before holdout
evaluation. The probes are rehydrated from the freeze artifact; no coefficient
or representation refit is allowed on holdout evidence.
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

from qore.infrastructure.core_stack_v2.representation_predictive_probe_v3 import (
    PredictiveIncrementalEvaluation,
    PredictiveIncrementalProbe,
    evaluate_predictive_incremental_probe,
    predictive_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    fit_predictive_representation,
)

SCHEMA = "qore.shared.wp04.predictive_holdout_eval_v3.v1"
IDENTITY = "QORE_SHARED_WP04_PREDICTIVE_HOLDOUT_A_V3_001"
HOLDOUT_PARTITION = "holdout_a"
HOLDOUT_START = datetime.fromisoformat("2022-07-18T00:00:00+00:00")
HOLDOUT_END_EXCLUSIVE = datetime.fromisoformat("2023-07-17T00:00:00+00:00")
MINIMUM_POOLED_INCREMENTAL_BPS = 100
MINIMUM_POSITIVE_TARGETS = 4


def _probe_from_payload(payload: dict[str, Any]) -> PredictiveIncrementalProbe:
    return PredictiveIncrementalProbe(
        fitted_at=datetime.fromisoformat(payload["fitted_at"]),
        calibration_partitions=tuple(payload["calibration_partitions"]),
        target_name=str(payload["target_name"]),
        representation_fingerprint=str(payload["representation_fingerprint"]),
        ontology_names=tuple(payload["ontology_names"]),
        concept_ids=tuple(payload["concept_ids"]),
        baseline_coefficients_micros=tuple(payload["baseline_coefficients_micros"]),
        augmented_coefficients_micros=tuple(payload["augmented_coefficients_micros"]),
        probe_fingerprint=str(payload["probe_fingerprint"]),
        representation_training_future_only=bool(
            payload["representation_training_future_only"]
        ),
        runtime_future_market_used=bool(payload["runtime_future_market_used"]),
        holdout_used_for_fit=bool(payload["holdout_used_for_fit"]),
        identity_used=bool(payload["identity_used"]),
        knowledge_promotion_authority=bool(
            payload["knowledge_promotion_authority"]
        ),
    )


def _summary(
    evaluations: list[PredictiveIncrementalEvaluation],
) -> dict[str, Any]:
    if not evaluations:
        raise ValueError("holdout summary requires evaluations")
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
    consumed: dict[str, dict[str, Path]],
    holdout: dict[str, Path],
) -> dict[str, Any]:
    freeze = json.loads(freeze_path.read_text())
    if freeze["status"] != "WP04_V3_PROBE_FROZEN_FOR_ONE_SHOT_HOLDOUT":
        raise ValueError("freeze artifact is not authorized for holdout")
    if freeze["probe_frozen_for_holdout"] is not True:
        raise ValueError("probe freeze gate did not pass")
    if freeze["fresh_holdout_opened"] is not False:
        raise ValueError("freeze artifact already reports fresh holdout opened")
    if len(freeze["final_frozen_probes"]) != 8:
        raise ValueError("freeze artifact must contain eight frozen probes")

    source_partitions = {}
    transitions = {}
    for partition in PARTITIONS:
        episodes, _source_range = _prepare_source_partition(
            partition=partition,
            evidence_paths=consumed[partition],
        )
        source_partitions[partition] = episodes
        transitions[partition] = _build_transitions(episodes)

    fitted_at = max(
        item.future.as_of
        for rows in transitions.values()
        for item in rows
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
        raise ValueError("frozen representation fingerprint drift")

    probes = {
        payload["target_name"]: _probe_from_payload(payload)
        for payload in freeze["final_frozen_probes"]
    }
    if len(probes) != 8:
        raise ValueError("frozen probe target names must be unique")
    if any(
        probe.representation_fingerprint != representation_fingerprint
        for probe in probes.values()
    ):
        raise ValueError("frozen probe representation fingerprint drift")
    if any(
        probe.calibration_partitions != ("r8", "r6", "r5")
        for probe in probes.values()
    ):
        raise ValueError("frozen probes must be calibrated on consumed partitions")
    if any(probe.holdout_used_for_fit for probe in probes.values()):
        raise ValueError("holdout cannot have participated in probe fit")

    holdout_episodes, holdout_targets, holdout_range = _prepare_partition(
        partition=HOLDOUT_PARTITION,
        evidence_paths=holdout,
    )
    if not holdout_episodes:
        raise ValueError("holdout contains no evaluation episodes")
    if min(item.as_of for item in holdout_episodes) < HOLDOUT_START:
        raise ValueError("holdout source evidence begins before preregistered start")
    if max(item.as_of for item in holdout_episodes) >= HOLDOUT_END_EXCLUSIVE:
        raise ValueError("holdout source evidence crosses preregistered end")
    for rows in holdout_targets.values():
        if any(item.observed_at >= HOLDOUT_END_EXCLUSIVE for item in rows):
            raise ValueError("holdout target evidence crosses preregistered end")

    evaluations = [
        evaluate_predictive_incremental_probe(
            model=model,
            probe=probes[target_name],
            partition=HOLDOUT_PARTITION,
            episodes=holdout_episodes,
            targets=holdout_targets[target_name],
        )
        for target_name in sorted(probes)
    ]
    summary = _summary(evaluations)
    all_probe_fingerprints = {
        probe.probe_fingerprint
        for probe in probes.values()
    }
    evaluation_probe_fingerprints = {
        item.probe_fingerprint
        for item in evaluations
    }
    if all_probe_fingerprints != evaluation_probe_fingerprints:
        raise ValueError("holdout evaluation probe fingerprint drift")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP04_V3_HOLDOUT_A_PASS_REPLICATION_REQUIRED"
            if summary["pass"]
            else "WP04_V3_HOLDOUT_A_FALSIFIED"
        ),
        "protocol_pass": True,
        "holdout_a_pass": summary["pass"],
        "replication_required": summary["pass"],
        "wp04_exit_gate_pass": False,
        "representation_fingerprint": representation_fingerprint,
        "probe_fingerprints": sorted(all_probe_fingerprints),
        "holdout": {
            "partition": HOLDOUT_PARTITION,
            "preregistered_start_inclusive": HOLDOUT_START.isoformat(),
            "preregistered_end_exclusive": HOLDOUT_END_EXCLUSIVE.isoformat(),
            "observed_source_min": min(
                item.as_of for item in holdout_episodes
            ).isoformat(),
            "observed_source_max": max(
                item.as_of for item in holdout_episodes
            ).isoformat(),
            "evaluation_range": holdout_range,
            "episode_count": len(holdout_episodes),
        },
        "evaluation": summary,
        "governance": {
            "holdout_preregistered_before_acquisition": True,
            "consumed_representation_refit_on_holdout": False,
            "probe_refit_on_holdout": False,
            "holdout_used_for_threshold_selection": False,
            "runtime_future_market_used": False,
            "identity_shortcut_used": False,
            "trade_outcome_or_pnl_used_as_feature": False,
            "replication_b_remains_sealed_until_holdout_a_pass": True,
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
    for partition in PARTITIONS:
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--holdout-nas", type=Path, required=True)
    parser.add_argument("--holdout-sp", type=Path, required=True)
    parser.add_argument("--holdout-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        freeze_path=args.freeze,
        consumed={
            partition: _paths(args, partition)
            for partition in PARTITIONS
        },
        holdout=_paths(args, "holdout"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "holdout_a_pass": payload["holdout_a_pass"],
                "pooled_incremental_information_bps": payload["evaluation"][
                    "pooled_incremental_information_bps"
                ],
                "positive_target_count": payload["evaluation"][
                    "positive_target_count"
                ],
                "replication_required": payload["replication_required"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
