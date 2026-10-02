#!/usr/bin/env python3
"""Replicated real-data stress proof for Shared X-10 Contradiction Map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.shared_contradiction_map import (
    ContradictionEvidence,
    build_contradiction_state,
)

IDENTITY="QORE_SHARED_X10_CONTRADICTION_MAP_REAL_REPLAY_001"
HYPOTHESIS="H1_WORLD_CONTINUATION"
GROUPS=("LOCAL","PEER","WORLD")


def _clip(value: int) -> int:
    return max(0,min(10_000,value))


def _evidence(observation: object, *, stress: bool) -> tuple[ContradictionEvidence,...]:
    o=observation
    local_support=(
        o.displacement_bps+o.acceptance_bps+o.momentum_persistence_bps
    )//3
    local_contra=(
        o.failed_auction_bps+o.momentum_decay_bps+o.structural_fragility_bps
    )//3
    peer_support=o.leader_confirmation_bps
    peer_contra=o.leader_divergence_bps
    world_support=(
        (10_000-o.regime_transition_bps)
        +(10_000-o.anomaly_bps)
    )//2
    world_contra=(o.regime_transition_bps+o.anomaly_bps)//2
    if stress:
        local_contra=_clip(local_contra+3_000)
        peer_contra=_clip(peer_contra+3_000)
        world_contra=_clip(world_contra+3_000)

    values=(
        ("local","LOCAL",local_support,local_contra),
        ("peer","PEER",peer_support,peer_contra),
        ("world","WORLD",world_support,world_contra),
    )
    return tuple(
        ContradictionEvidence(
            evidence_id=f"{name}:{o.observation_id}",
            hypothesis_id=HYPOTHESIS,
            as_of=o.as_of,
            support_bps=support,
            contradiction_bps=contradiction,
            data_quality_bps=o.data_integrity_bps,
            independent_group=group,
            evidence_refs=o.provenance_refs,
        )
        for name,group,support,contradiction in values
    )


def _mean(values: list[int]) -> int:
    return sum(values)//len(values) if values else 0


def _partition(paths: dict[str,Path], *, partition: str) -> dict[str,object]:
    rows=source._aligned_source_rows(paths,partition=partition,require_future=False)
    if not rows:
        raise ValueError("contradiction replay has no source rows")

    baseline=[]
    stressed=[]
    for observation,*_ in rows:
        baseline.append(
            build_contradiction_state(
                _evidence(observation,stress=False),
                hypothesis_id=HYPOTHESIS,
                required_groups=GROUPS,
            )
        )
        stressed.append(
            build_contradiction_state(
                _evidence(observation,stress=True),
                hypothesis_id=HYPOTHESIS,
                required_groups=GROUPS,
            )
        )

    base_contra=_mean([x.contradiction_bps for x in baseline])
    stress_contra=_mean([x.contradiction_bps for x in stressed])
    base_assert=_mean([x.assertiveness_ceiling_bps for x in baseline])
    stress_assert=_mean([x.assertiveness_ceiling_bps for x in stressed])
    missing=sum(bool(x.missing_evidence) for x in baseline)
    gate=(
        stress_contra-base_contra >= 1_500
        and base_assert-stress_assert >= 1_000
        and missing == 0
    )
    return {
        "sample_count":len(rows),
        "baseline_contradiction_bps":base_contra,
        "stressed_contradiction_bps":stress_contra,
        "contradiction_delta_bps":stress_contra-base_contra,
        "baseline_assertiveness_ceiling_bps":base_assert,
        "stressed_assertiveness_ceiling_bps":stress_assert,
        "assertiveness_reduction_bps":base_assert-stress_assert,
        "baseline_missing_evidence_count":missing,
        "gate_pass":gate,
    }


def main() -> None:
    parser=argparse.ArgumentParser()
    for partition in ("r8","r6","r5"):
        for market in ("nas","sp","us"):
            parser.add_argument(f"--{partition}-{market}",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()

    results={}
    for partition in ("r8","r6","r5"):
        results[partition]=_partition(
            {
                "NAS100":getattr(args,f"{partition}_nas"),
                "SP500":getattr(args,f"{partition}_sp"),
                "US30":getattr(args,f"{partition}_us"),
            },
            partition=partition,
        )
    passed=all(results[p]["gate_pass"] for p in ("r8","r6","r5"))
    payload={
        "identity":IDENTITY,
        "status":(
            "X10_CONTRADICTION_MAP_REPLICATED_PASS"
            if passed else "X10_CONTRADICTION_MAP_FALSIFIED"
        ),
        "results":results,
        "engine_implemented":True,
        "real_data_bound":True,
        "causal_replay_executed":True,
        "fault_injection_stress":True,
        "temporal_replication_r8_r6_r5":passed,
        "future_market_used":False,
        "outcome_or_pnl_used":False,
        "economic_value_required":False,
        "economic_value_reason":"epistemic cognition only; no trading action",
        "protected_certification_holdout_opened":False,
        "productive_authority":False,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":payload["status"]},sort_keys=True))


if __name__=="__main__":
    main()
