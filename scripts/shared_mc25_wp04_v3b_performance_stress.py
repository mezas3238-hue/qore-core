#!/usr/bin/env python3
"""MC-25 same-lineage WP04 V3B performance stress on consumed evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shared_wp04_historical_representation_discovery import _prepare_partition
from shared_wp04_invariant_representation_v2 import (
    PARTITIONS,
    _prepare_source_partition,
)
from shared_wp04_predictive_nonlinear_holdout_e_eval_v3b import (
    _probe_from_payload,
)
from shared_wp04_predictive_representation_v3 import (
    POLICY,
    _build_transitions,
)

from qore.infrastructure.core_stack_v2.mc25_v3b_performance_stress import (
    FROZEN_STRESS_SCENARIOS,
    apply_v3b_performance_stress,
    summarize_v3b_stress_evaluations,
)
from qore.infrastructure.core_stack_v2.representation_predictive_nonlinear_probe_v3b import (
    evaluate_predictive_second_order_probe_prepared,
    prepare_second_order_design,
)
from qore.infrastructure.core_stack_v2.representation_predictive_probe_v3 import (
    predictive_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    fit_predictive_representation,
)

IDENTITY = "QORE_SHARED_MC25_WP04_V3B_PERFORMANCE_STRESS_001"
EXPECTED_REPRESENTATION = (
    "e2fc2ca059d5852b4e9107c467392e5e64aeabbd6aca2d8013951b93402bc987"
)
HOLDOUT_START = datetime.fromisoformat("2026-07-13T00:00:00+00:00")
HOLDOUT_END = datetime.fromisoformat("2026-09-25T00:00:00+00:00")
REPLICATION_START = datetime.fromisoformat("2025-07-14T00:00:00+00:00")
REPLICATION_END = datetime.fromisoformat("2026-07-13T00:00:00+00:00")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _validate_prior_lineage(
    *,
    freeze: dict[str, Any],
    holdout_result: dict[str, Any],
    replication_result: dict[str, Any],
) -> None:
    if freeze.get("status") != "WP04_V3B_PROBE_FROZEN_FOR_ONE_SHOT_HOLDOUT":
        raise ValueError("V3B freeze status drift")
    if freeze.get("development_gate_pass") is not True:
        raise ValueError("V3B development gate drift")
    if freeze.get("representation", {}).get("fingerprint") != EXPECTED_REPRESENTATION:
        raise ValueError("V3B representation fingerprint drift")
    if holdout_result.get("status") != (
        "WP04_V3B_HOLDOUT_E_PASS_REPLICATION_REQUIRED"
    ):
        raise ValueError("HOLDOUT_E is not the sealed PASS result")
    if holdout_result.get("holdout_e_pass") is not True:
        raise ValueError("HOLDOUT_E pass drift")
    if replication_result.get("status") != "WP04_V3B_REPLICATION_D_PASS":
        raise ValueError("REPLICATION_D is not the sealed PASS result")
    if replication_result.get("replication_d_pass") is not True:
        raise ValueError("REPLICATION_D pass drift")

    for payload in (holdout_result, replication_result):
        evaluation = payload.get("evaluation")
        if not isinstance(evaluation, dict):
            raise ValueError("V3B evaluation missing")
        if evaluation.get("minimum_pooled_incremental_bps") != 100:
            raise ValueError("V3B pooled gate drift")
        if evaluation.get("minimum_positive_target_count") != 4:
            raise ValueError("V3B positive-target gate drift")
        if payload.get("representation_fingerprint") != EXPECTED_REPRESENTATION:
            raise ValueError("V3B evaluation representation drift")


def _rebuild_model(
    consumed: dict[str, dict[str, Path]],
):
    transitions = {}
    for partition in PARTITIONS:
        episodes, _source_range = _prepare_source_partition(
            partition=partition,
            evidence_paths=consumed[partition],
        )
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
    if predictive_representation_fingerprint(model) != EXPECTED_REPRESENTATION:
        raise ValueError("V3B stress rebuild representation drift")
    return model


def _filter_targets(
    targets: dict[str, tuple[Any, ...]],
    *,
    start: datetime,
    end: datetime,
) -> dict[str, tuple[Any, ...]]:
    return {
        name: tuple(
            item
            for item in rows
            if start <= item.observed_at < end
        )
        for name, rows in targets.items()
    }


def _evaluate_partition(
    *,
    partition: str,
    model,
    probes,
    episodes,
    targets,
) -> dict[str, object]:
    prepared = prepare_second_order_design(
        model=model,
        episodes=episodes,
    )
    scenario_rows: list[dict[str, Any]] = []
    scenario_pass_count = 0
    for scenario in FROZEN_STRESS_SCENARIOS:
        stressed = apply_v3b_performance_stress(
            prepared,
            scenario,
        )
        evaluations = [
            evaluate_predictive_second_order_probe_prepared(
                model=model,
                probe=probes[target_name],
                partition=partition,
                prepared=stressed,
                targets=targets[target_name],
            )
            for target_name in sorted(probes)
        ]
        summary = summarize_v3b_stress_evaluations(evaluations)
        scenario_pass_count += int(bool(summary["pass"]))
        scenario_rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "kind": scenario.kind.value,
                "drop_bps": scenario.drop_bps,
                "attenuation_bps": scenario.attenuation_bps,
                "quantization_milli": scenario.quantization_milli,
                "evaluation": summary,
            }
        )
    return {
        "partition": partition,
        "scenario_count": len(scenario_rows),
        "scenario_pass_count": scenario_pass_count,
        "all_scenarios_pass": (
            scenario_pass_count == len(FROZEN_STRESS_SCENARIOS)
        ),
        "scenarios": scenario_rows,
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
    parser.add_argument("--holdout-result", type=Path, required=True)
    parser.add_argument("--replication-result", type=Path, required=True)
    for partition in PARTITIONS:
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    for prefix in ("holdout", "replication"):
        parser.add_argument(f"--{prefix}-nas", type=Path, required=True)
        parser.add_argument(f"--{prefix}-sp", type=Path, required=True)
        parser.add_argument(f"--{prefix}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    freeze = _load(args.freeze)
    holdout_result = _load(args.holdout_result)
    replication_result = _load(args.replication_result)
    _validate_prior_lineage(
        freeze=freeze,
        holdout_result=holdout_result,
        replication_result=replication_result,
    )

    model = _rebuild_model(
        {
            partition: _paths(args, partition)
            for partition in PARTITIONS
        }
    )
    probes = {
        payload["target_name"]: _probe_from_payload(payload)
        for payload in freeze["final_frozen_probes"]
    }
    if len(probes) != 8:
        raise ValueError("V3B stress requires eight frozen probes")

    holdout_episodes, holdout_targets, _ = _prepare_partition(
        partition="holdout_e",
        evidence_paths=_paths(args, "holdout"),
    )
    holdout_episodes = tuple(
        item
        for item in holdout_episodes
        if HOLDOUT_START <= item.as_of < HOLDOUT_END
    )
    holdout_targets = _filter_targets(
        holdout_targets,
        start=HOLDOUT_START,
        end=HOLDOUT_END,
    )

    replication_episodes, replication_targets, _ = _prepare_partition(
        partition="replication_d",
        evidence_paths=_paths(args, "replication"),
    )
    replication_episodes = tuple(
        item
        for item in replication_episodes
        if REPLICATION_START <= item.as_of < REPLICATION_END
    )
    replication_targets = _filter_targets(
        replication_targets,
        start=REPLICATION_START,
        end=REPLICATION_END,
    )

    if set(holdout_targets) != set(probes):
        raise ValueError("HOLDOUT_E target schema drift")
    if set(replication_targets) != set(probes):
        raise ValueError("REPLICATION_D target schema drift")

    results = {
        "HOLDOUT_E": _evaluate_partition(
            partition="holdout_e",
            model=model,
            probes=probes,
            episodes=holdout_episodes,
            targets=holdout_targets,
        ),
        "REPLICATION_D": _evaluate_partition(
            partition="replication_d",
            model=model,
            probes=probes,
            episodes=replication_episodes,
            targets=replication_targets,
        ),
    }
    performance_pass = all(
        bool(row["all_scenarios_pass"])
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC25_WP04_V3B_PERFORMANCE_STRESS_PASS"
            if performance_pass
            else "MC25_WP04_V3B_PERFORMANCE_STRESS_FALSIFIED"
        ),
        "representation_fingerprint": EXPECTED_REPRESENTATION,
        "frozen_probe_fingerprints": sorted(
            probe.probe_fingerprint
            for probe in probes.values()
        ),
        "frozen_original_gates": {
            "minimum_pooled_incremental_bps": 100,
            "minimum_positive_target_count": 4,
        },
        "stress_scenario_count": len(FROZEN_STRESS_SCENARIOS),
        "partition_count": len(results),
        "results": results,
        "performance_stress_bound": True,
        "performance_stress_pass": performance_pass,
        "formal_stress_stage_completed": performance_pass,
        "highest_formal_stage": (
            "STRESS" if performance_pass else "HOLDOUT"
        ),
        "shadow_stage_bound": False,
        "certification_stage_bound": False,
        "promotion_allowed": False,
        "mc25_completed_and_proven": False,
        "next_gate": (
            "WP04_V3B_GOVERNED_SHADOW"
            if performance_pass
            else "FALSIFIED_AND_CLOSED_FOR_THIS_STRESS_CONFIGURATION"
        ),
        "probe_refit": False,
        "representation_refit": False,
        "threshold_retuning": False,
        "target_aware_stress_selection": False,
        "knowledge_auto_promotion": False,
        "productive_authority": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "performance_stress_pass": performance_pass,
                "highest_formal_stage": payload["highest_formal_stage"],
                "next_gate": payload["next_gate"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
