"""WP-05 consumed target-semantics audit.

This audit does not fit a model and does not change the existing target.
It measures whether the historical terminal label used by WP-05 points in the
same direction as the higher-timeframe structural-failure concept defined by
issue #643.

Evidence is already-consumed R8/R6/R5 only. No fresh holdout is opened.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shared_wp05_temporal_hierarchy_absorption_v3 import (
    PARTITIONS,
    _paths,
    _prepare_partition,
)

from qore.infrastructure.core_stack_v2.temporal_hierarchy_target_contract import (
    assess_temporal_hierarchy_target_semantics,
)

SCHEMA = "qore.shared.wp05.target_semantics_audit_consumed.v1"
IDENTITY = "QORE_SHARED_WP05_TARGET_SEMANTICS_AUDIT_V1_001"


def _audit_partition(
    episodes: tuple[Any, ...],
) -> dict[str, int]:
    baseline = 0
    identifiable = 0
    aligned = 0
    inverted = 0
    unidentifiable = 0
    terminals = 0
    terminal_aligned = 0
    terminal_inverted = 0
    terminal_unidentifiable = 0

    for item in episodes:
        snapshot = item.trajectory.snapshots[-1]
        audit = assess_temporal_hierarchy_target_semantics(snapshot)
        if not audit.baseline_local_opposition:
            continue
        baseline += 1
        if item.terminal_failure:
            terminals += 1

        if not audit.directionally_identifiable:
            unidentifiable += 1
            if item.terminal_failure:
                terminal_unidentifiable += 1
            continue

        identifiable += 1
        if audit.directionally_aligned:
            aligned += 1
            if item.terminal_failure:
                terminal_aligned += 1
        elif audit.directionally_inverted:
            inverted += 1
            if item.terminal_failure:
                terminal_inverted += 1
        else:
            raise AssertionError("identifiable target semantics must classify")

    denominator = max(1, identifiable)
    return {
        "baseline_opposition_count": baseline,
        "directionally_identifiable_count": identifiable,
        "directionally_aligned_count": aligned,
        "directionally_inverted_count": inverted,
        "directionally_unidentifiable_count": unidentifiable,
        "directional_alignment_bps": aligned * 10_000 // denominator,
        "directional_inversion_bps": inverted * 10_000 // denominator,
        "terminal_count": terminals,
        "terminal_aligned_count": terminal_aligned,
        "terminal_inverted_count": terminal_inverted,
        "terminal_unidentifiable_count": terminal_unidentifiable,
    }


def run(*, evidence: dict[str, dict[str, Path]]) -> dict[str, Any]:
    evaluations: dict[str, dict[str, int]] = {}
    ranges: dict[str, dict[str, str | int | None]] = {}

    for partition in PARTITIONS:
        episodes, partition_range = _prepare_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        evaluations[partition] = _audit_partition(episodes)
        ranges[partition] = partition_range

    material_inversion = any(
        evaluations[partition]["directional_inversion_bps"] >= 500
        for partition in PARTITIONS
    )
    protocol_pass = all(
        evaluations[partition]["baseline_opposition_count"] > 0
        for partition in PARTITIONS
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP05_TARGET_CONTRACT_DIRECTIONALLY_INCONSISTENT"
            if protocol_pass and material_inversion
            else "WP05_TARGET_CONTRACT_DIRECTIONALLY_CONSISTENT"
            if protocol_pass
            else "WP05_TARGET_SEMANTICS_AUDIT_FAILED"
        ),
        "protocol_pass": protocol_pass,
        "target_contract_pass": protocol_pass and not material_inversion,
        "fresh_holdout_opened": False,
        "partition_ranges": ranges,
        "evaluations": evaluations,
        "semantic_contract": {
            "wp05_question": (
                "local adverse pressure versus genuine higher-timeframe "
                "structural failure"
            ),
            "current_consumed_target_orientation": "OPPOSITE_M15_DIRECTION",
            "expected_structural_failure_orientation": (
                "OPPOSITE_HIGHER_TIMEFRAME_ANCHOR"
            ),
            "material_inversion_threshold_bps": 500,
            "audit_changes_target": False,
            "audit_fits_model": False,
        },
        "governance": {
            "consumed_r8_r6_r5_only": True,
            "fresh_holdout_opened": False,
            "target_changed": False,
            "threshold_changed": False,
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
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_pass": payload["protocol_pass"],
                "target_contract_pass": payload["target_contract_pass"],
                "evaluations": payload["evaluations"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
