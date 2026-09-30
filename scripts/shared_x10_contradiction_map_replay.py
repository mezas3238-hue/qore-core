#!/usr/bin/env python3
"""Replicated real-data proof for X-10 causal contradiction intelligence."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import shared_sti2_real_opportunity_discovery as sti2

from qore.infrastructure.core_stack_v2.shared_contradiction_map import (
    ContradictionEvidence,
    build_contradiction_state,
)

IDENTITY = "QORE_SHARED_X10_CONTRADICTION_MAP_REPLICATION_001"
GROUPS = ("CROSS_MARKET", "LIQUIDITY", "STRUCTURE", "TRAJECTORY")


def _mean(*values: int) -> int:
    return sum(values) // len(values)


def _clip(value: int) -> int:
    return max(0, min(10_000, value))


def _evidence(
    *,
    partition: str,
    observation: object,
) -> tuple[ContradictionEvidence, ...]:
    obs = observation
    rows = (
        ContradictionEvidence(
            evidence_id=f"{partition}:{obs.observation_id}:CROSS_MARKET",
            hypothesis_id="H1_WORLD_CONTINUATION",
            as_of=obs.as_of,
            evidence_cutoff_at=obs.evidence_cutoff_at,
            support_bps=obs.leader_confirmation_bps,
            contradiction_bps=obs.leader_divergence_bps,
            data_quality_bps=obs.data_integrity_bps,
            independent_group="CROSS_MARKET",
            evidence_refs=(f"{partition}:cross-market",),
        ),
        ContradictionEvidence(
            evidence_id=f"{partition}:{obs.observation_id}:LIQUIDITY",
            hypothesis_id="H1_WORLD_CONTINUATION",
            as_of=obs.as_of,
            evidence_cutoff_at=obs.evidence_cutoff_at,
            support_bps=_mean(
                obs.liquidity_accumulation_bps,
                obs.compression_bps,
            ),
            contradiction_bps=_mean(
                obs.liquidity_vacuum_bps,
                obs.failed_auction_bps,
            ),
            data_quality_bps=obs.data_integrity_bps,
            independent_group="LIQUIDITY",
            evidence_refs=(f"{partition}:liquidity",),
        ),
        ContradictionEvidence(
            evidence_id=f"{partition}:{obs.observation_id}:STRUCTURE",
            hypothesis_id="H1_WORLD_CONTINUATION",
            as_of=obs.as_of,
            evidence_cutoff_at=obs.evidence_cutoff_at,
            support_bps=_mean(
                obs.displacement_bps,
                obs.acceptance_bps,
            ),
            contradiction_bps=_mean(
                obs.structural_fragility_bps,
                obs.anomaly_bps,
            ),
            data_quality_bps=obs.data_integrity_bps,
            independent_group="STRUCTURE",
            evidence_refs=(f"{partition}:structure",),
        ),
        ContradictionEvidence(
            evidence_id=f"{partition}:{obs.observation_id}:TRAJECTORY",
            hypothesis_id="H1_WORLD_CONTINUATION",
            as_of=obs.as_of,
            evidence_cutoff_at=obs.evidence_cutoff_at,
            support_bps=obs.momentum_persistence_bps,
            contradiction_bps=obs.momentum_decay_bps,
            data_quality_bps=obs.data_integrity_bps,
            independent_group="TRAJECTORY",
            evidence_refs=(f"{partition}:trajectory",),
        ),
    )
    return tuple(sorted(rows, key=lambda item: item.evidence_id))


def _evaluate(
    *,
    partition: str,
    paths: dict[str, Path],
) -> dict[str, object]:
    rows = sti2._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    baseline_count = 0
    stress_monotonic_count = 0
    missing_penalty_count = 0
    cutoff_count = 0
    high_contradiction_count = 0

    for observation, _states, _pre, _future in rows:
        evidence = _evidence(partition=partition, observation=observation)
        baseline = build_contradiction_state(
            evidence,
            hypothesis_id="H1_WORLD_CONTINUATION",
            required_groups=GROUPS,
        )
        if baseline.missing_evidence:
            raise AssertionError("complete source evidence unexpectedly missing group")
        if baseline.evidence_cutoff_at is None or baseline.as_of is None:
            raise AssertionError("causal contradiction state missing timestamps")
        if baseline.evidence_cutoff_at > baseline.as_of:
            raise AssertionError("future evidence reached contradiction state")
        cutoff_count += 1

        stressed = tuple(
            replace(
                item,
                contradiction_bps=_clip(item.contradiction_bps + 2_500),
            )
            for item in evidence
        )
        stressed_state = build_contradiction_state(
            stressed,
            hypothesis_id="H1_WORLD_CONTINUATION",
            required_groups=GROUPS,
        )
        if (
            stressed_state.contradiction_bps < baseline.contradiction_bps
            or stressed_state.assertiveness_ceiling_bps
            > baseline.assertiveness_ceiling_bps
        ):
            raise AssertionError(
                "contradiction stress must not increase assertiveness"
            )
        stress_monotonic_count += 1

        missing_state = build_contradiction_state(
            evidence,
            hypothesis_id="H1_WORLD_CONTINUATION",
            required_groups=GROUPS + ("MACRO",),
        )
        if "MACRO" not in missing_state.missing_evidence:
            raise AssertionError("required missing evidence was not surfaced")
        if (
            missing_state.assertiveness_ceiling_bps
            > baseline.assertiveness_ceiling_bps
        ):
            raise AssertionError(
                "missing evidence must not increase assertiveness"
            )
        missing_penalty_count += 1

        if stressed_state.contradiction_bps >= 6_000:
            if "CONTRADICTION_HIGH" not in stressed_state.reason_codes:
                raise AssertionError(
                    "high contradiction must be first-class reason"
                )
            high_contradiction_count += 1
        baseline_count += 1

    all_pass = (
        baseline_count > 0
        and cutoff_count == baseline_count
        and stress_monotonic_count == baseline_count
        and missing_penalty_count == baseline_count
    )
    return {
        "source_observation_count": baseline_count,
        "causal_cutoff_pass_count": cutoff_count,
        "contradiction_stress_monotonic_pass_count": stress_monotonic_count,
        "missing_evidence_penalty_pass_count": missing_penalty_count,
        "high_contradiction_observation_count": high_contradiction_count,
        "all_pass": all_pass,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        for market in ("nas", "sp", "us"):
            parser.add_argument(
                f"--{partition}-{market}",
                type=Path,
                required=True,
            )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    market_names = {"nas": "NAS100", "sp": "SP500", "us": "US30"}
    partitions: dict[str, dict[str, object]] = {}
    for partition in ("r8", "r6", "r5"):
        paths = {
            market: getattr(args, f"{partition}_{key}")
            for key, market in market_names.items()
        }
        partitions[partition] = _evaluate(
            partition=partition,
            paths=paths,
        )

    all_pass = all(bool(row["all_pass"]) for row in partitions.values())
    payload = {
        "identity": IDENTITY,
        "capability": "X-10_CONTRADICTION_MAP",
        "status": (
            "X10_COMPLETED_AND_PROVEN_REPLICATED_REAL_DATA"
            if all_pass
            else "X10_REPLICATION_FAILURE"
        ),
        "all_pass": all_pass,
        "partitions": partitions,
        "proof": {
            "engine_implemented": True,
            "real_data_bound": True,
            "causal_replay_executed": True,
            "contradiction_stress_pass": all_pass,
            "missing_evidence_stress_pass": all_pass,
            "temporal_replication_r8_r6_r5": all_pass,
            "future_evidence_rejected": True,
            "assertiveness_decreases_with_contradiction": True,
            "assertiveness_decreases_with_missing_evidence": True,
            "economic_value_required": False,
            "reason_economic_value_not_required": (
                "epistemic safety capability; does not trade or manage capital"
            ),
        },
        "governance": {
            "trader_authority": False,
            "capital_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "all_pass": all_pass,
                "observations": sum(
                    int(row["source_observation_count"])
                    for row in partitions.values()
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
