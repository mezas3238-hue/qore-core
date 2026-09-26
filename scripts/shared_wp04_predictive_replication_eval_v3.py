"""Pre-registered temporal replication evaluator for WP-04 V3.

REPLICATION_B may be evaluated only after HOLDOUT_A passes. It reuses the exact
same consumed-data representation fingerprint and frozen probe fingerprints.
No representation, probe, threshold or methodology refit is permitted.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shared_wp04_historical_representation_discovery import _prepare_partition
from shared_wp04_invariant_representation_v2 import PARTITIONS, _prepare_source_partition
from shared_wp04_predictive_holdout_eval_v3 import _probe_from_payload, _summary
from shared_wp04_predictive_representation_v3 import POLICY, _build_transitions

from qore.infrastructure.core_stack_v2.representation_predictive_probe_v3 import (
    evaluate_predictive_incremental_probe,
    predictive_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    fit_predictive_representation,
)

SCHEMA = "qore.shared.wp04.predictive_replication_eval_v3.v1"
IDENTITY = "QORE_SHARED_WP04_PREDICTIVE_REPLICATION_B_V3_001"
REPLICATION_PARTITION = "replication_b"
REPLICATION_START = datetime.fromisoformat("2023-07-17T00:00:00+00:00")
REPLICATION_END_EXCLUSIVE = datetime.fromisoformat("2024-07-15T00:00:00+00:00")


def run(
    *,
    freeze_path: Path,
    holdout_a_result_path: Path,
    consumed: dict[str, dict[str, Path]],
    replication: dict[str, Path],
) -> dict[str, Any]:
    freeze = json.loads(freeze_path.read_text())
    holdout_a = json.loads(holdout_a_result_path.read_text())

    if freeze["status"] != "WP04_V3_PROBE_FROZEN_FOR_ONE_SHOT_HOLDOUT":
        raise ValueError("freeze artifact is not authorized for replication")
    if freeze["probe_frozen_for_holdout"] is not True:
        raise ValueError("probe freeze gate did not pass")
    if holdout_a["status"] != "WP04_V3_HOLDOUT_A_PASS_REPLICATION_REQUIRED":
        raise ValueError("REPLICATION_B requires HOLDOUT_A PASS")
    if holdout_a["holdout_a_pass"] is not True:
        raise ValueError("HOLDOUT_A did not pass")
    if holdout_a["replication_required"] is not True:
        raise ValueError("HOLDOUT_A result does not authorize replication")

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
    if representation_fingerprint != holdout_a["representation_fingerprint"]:
        raise ValueError("HOLDOUT_A representation fingerprint drift")

    probes = {
        payload["target_name"]: _probe_from_payload(payload)
        for payload in freeze["final_frozen_probes"]
    }
    freeze_probe_fingerprints = sorted(
        probe.probe_fingerprint for probe in probes.values()
    )
    if freeze_probe_fingerprints != sorted(holdout_a["probe_fingerprints"]):
        raise ValueError("HOLDOUT_A probe fingerprint drift")

    replication_episodes, replication_targets, replication_range = _prepare_partition(
        partition=REPLICATION_PARTITION,
        evidence_paths=replication,
    )
    if not replication_episodes:
        raise ValueError("replication contains no evaluation episodes")
    if min(item.as_of for item in replication_episodes) < REPLICATION_START:
        raise ValueError("replication starts before preregistered boundary")
    if max(item.as_of for item in replication_episodes) >= REPLICATION_END_EXCLUSIVE:
        raise ValueError("replication crosses preregistered end")
    for rows in replication_targets.values():
        if any(item.observed_at >= REPLICATION_END_EXCLUSIVE for item in rows):
            raise ValueError("replication target crosses preregistered end")

    evaluations = [
        evaluate_predictive_incremental_probe(
            model=model,
            probe=probes[target_name],
            partition=REPLICATION_PARTITION,
            episodes=replication_episodes,
            targets=replication_targets[target_name],
        )
        for target_name in sorted(probes)
    ]
    summary = _summary(evaluations)
    evaluated_fingerprints = sorted(
        item.probe_fingerprint for item in evaluations
    )
    if evaluated_fingerprints != freeze_probe_fingerprints:
        raise ValueError("replication probe fingerprint drift")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP04_V3_REPLICATION_B_PASS"
            if summary["pass"]
            else "WP04_V3_REPLICATION_B_FALSIFIED"
        ),
        "protocol_pass": True,
        "holdout_a_pass_bound": True,
        "replication_b_pass": summary["pass"],
        "wp04_exit_gate_pass": summary["pass"],
        "representation_fingerprint": representation_fingerprint,
        "probe_fingerprints": freeze_probe_fingerprints,
        "replication": {
            "partition": REPLICATION_PARTITION,
            "preregistered_start_inclusive": REPLICATION_START.isoformat(),
            "preregistered_end_exclusive": REPLICATION_END_EXCLUSIVE.isoformat(),
            "observed_source_min": min(
                item.as_of for item in replication_episodes
            ).isoformat(),
            "observed_source_max": max(
                item.as_of for item in replication_episodes
            ).isoformat(),
            "evaluation_range": replication_range,
            "episode_count": len(replication_episodes),
        },
        "evaluation": summary,
        "governance": {
            "holdout_a_pass_required_and_bound": True,
            "replication_preregistered_before_holdout_a_open": True,
            "representation_refit_on_replication": False,
            "probe_refit_on_replication": False,
            "threshold_retuning_on_replication": False,
            "runtime_future_market_used": False,
            "identity_shortcut_used": False,
            "trade_outcome_or_pnl_used_as_feature": False,
            "knowledge_auto_promotion": False,
            "global_qore_validation_still_required": True,
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
    parser.add_argument("--holdout-a-result", type=Path, required=True)
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
        holdout_a_result_path=args.holdout_a_result,
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
                "replication_b_pass": payload["replication_b_pass"],
                "wp04_exit_gate_pass": payload["wp04_exit_gate_pass"],
                "pooled_incremental_information_bps": payload["evaluation"][
                    "pooled_incremental_information_bps"
                ],
                "positive_target_count": payload["evaluation"][
                    "positive_target_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
