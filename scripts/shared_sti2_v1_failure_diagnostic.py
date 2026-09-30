#!/usr/bin/env python3
"""Extract scientific knowledge from falsified STI-2 V1 without retuning it.

The diagnostic replays the exact frozen STI-2 policy on already-consumed R6/R5
evidence and profiles TP/FP/FN/TN source states. It may generate mechanistic V2
research hypotheses, but it may not change V1 thresholds, policy or engine.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any, cast

import shared_sti2_real_opportunity_discovery as sti2

from qore.infrastructure.core_stack_v2.dynamic_causal_graph import CausalConcept
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
    assess_global_opportunity,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
)

IDENTITY = "QORE_SHARED_STI2_V1_FAILURE_DIAGNOSTIC_001"

FEATURES = (
    "compression_bps",
    "liquidity_accumulation_bps",
    "failed_auction_bps",
    "displacement_bps",
    "acceptance_bps",
    "absorption_bps",
    "leader_confirmation_bps",
    "leader_divergence_bps",
    "momentum_persistence_bps",
    "momentum_decay_bps",
    "structural_fragility_bps",
    "liquidity_vacuum_bps",
    "regime_transition_bps",
    "anomaly_bps",
)


def _mean(rows: list[dict[str, int]], key: str) -> int:
    if not rows:
        return 0
    return sum(row[key] for row in rows) // len(rows)


def _dominant_target(target: dict[CausalConcept, int]) -> str:
    candidates = (
        CausalConcept.EXPANSION_READINESS,
        CausalConcept.DISPLACEMENT,
        CausalConcept.CONTINUATION,
        CausalConcept.REVERSAL,
    )
    return max(candidates, key=lambda item: (target[item], item.value)).value


def _profile(
    rows: list[dict[str, int]],
) -> dict[str, int]:
    return {feature: _mean(rows, feature) for feature in FEATURES}


def _delta(
    left: dict[str, int],
    right: dict[str, int],
) -> dict[str, int]:
    return {feature: left[feature] - right[feature] for feature in FEATURES}


def _hypotheses(
    *,
    fn_profile: dict[str, int],
    tn_profile: dict[str, int],
    fn_maturity: Counter[str],
    fn_target: Counter[str],
) -> list[dict[str, object]]:
    delta = _delta(fn_profile, tn_profile)
    candidates: list[dict[str, object]] = []

    accumulation = max(
        delta["compression_bps"],
        delta["liquidity_accumulation_bps"],
        delta["liquidity_vacuum_bps"],
    )
    if accumulation >= 500:
        candidates.append(
            {
                "hypothesis": "V2_SEQUENTIAL_ACCUMULATION_AND_RELEASE",
                "evidence": {
                    "max_fn_minus_tn_source_delta_bps": accumulation,
                    "features": {
                        key: delta[key]
                        for key in (
                            "compression_bps",
                            "liquidity_accumulation_bps",
                            "liquidity_vacuum_bps",
                        )
                    },
                },
                "meaning": (
                    "Missed opportunities may require temporal accumulation/release "
                    "rather than a single-state opportunity score."
                ),
            }
        )

    relation = max(
        delta["leader_divergence_bps"],
        delta["regime_transition_bps"],
        delta["structural_fragility_bps"],
    )
    if relation >= 500:
        candidates.append(
            {
                "hypothesis": "V2_RELATIONSHIP_TRANSITION_AS_OPPORTUNITY_PRECURSOR",
                "evidence": {
                    "max_fn_minus_tn_source_delta_bps": relation,
                    "features": {
                        key: delta[key]
                        for key in (
                            "leader_divergence_bps",
                            "regime_transition_bps",
                            "structural_fragility_bps",
                        )
                    },
                },
                "meaning": (
                    "Opportunity emergence may begin as relation/world transition "
                    "before directional support becomes mature."
                ),
            }
        )

    momentum = max(
        delta["momentum_decay_bps"],
        delta["failed_auction_bps"],
        delta["absorption_bps"],
    )
    if momentum >= 500:
        candidates.append(
            {
                "hypothesis": "V2_REVERSAL_PRECURSOR_SEQUENCE",
                "evidence": {
                    "max_fn_minus_tn_source_delta_bps": momentum,
                    "features": {
                        key: delta[key]
                        for key in (
                            "momentum_decay_bps",
                            "failed_auction_bps",
                            "absorption_bps",
                        )
                    },
                },
                "meaning": (
                    "A subset of missed opportunities may be reversal precursors "
                    "whose causal order matters more than their instantaneous mean."
                ),
            }
        )

    low_maturity = sum(
        count
        for state, count in fn_maturity.items()
        if state in {
            SharedOpportunityMaturity.NO_OPPORTUNITY.value,
            SharedOpportunityMaturity.EARLY.value,
        }
    )
    total_fn = sum(fn_maturity.values())
    if total_fn and low_maturity * 10_000 // total_fn >= 7_000:
        candidates.append(
            {
                "hypothesis": "V2_MATURITY_MODEL_MISSES_EARLY_CAUSAL_TRAJECTORY",
                "evidence": {
                    "fn_no_opportunity_or_early_bps": (
                        low_maturity * 10_000 // total_fn
                    ),
                    "fn_maturity_histogram": dict(sorted(fn_maturity.items())),
                },
                "meaning": (
                    "The V1 maturity construction may be structurally late; V2 "
                    "should model opportunity journey, not lower V1 thresholds."
                ),
            }
        )

    if fn_target:
        dominant, count = fn_target.most_common(1)[0]
        total = sum(fn_target.values())
        candidates.append(
            {
                "hypothesis": "V2_TARGET_MECHANISM_SPECIFIC_HEADS",
                "evidence": {
                    "dominant_missed_future_mechanism": dominant,
                    "dominant_share_bps": count * 10_000 // total,
                    "target_histogram": dict(sorted(fn_target.items())),
                },
                "meaning": (
                    "Expansion, displacement, continuation and reversal may need "
                    "separate causal heads before arbitration instead of one max score."
                ),
            }
        )

    return candidates


def diagnose_partition(
    *,
    partition: str,
    paths: dict[str, Path],
    frozen: dict[str, Any],
) -> dict[str, object]:
    policy = sti2._policy_from_payload(frozen)
    rows = sti2._aligned_source_rows(
        paths,
        partition=partition,
        require_future=True,
    )
    history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=policy.sequence_window
    )
    buckets: dict[str, list[dict[str, int]]] = {
        "TP": [],
        "FP": [],
        "FN": [],
        "TN": [],
    }
    maturity: dict[str, Counter[str]] = {
        key: Counter() for key in buckets
    }
    future_targets: dict[str, Counter[str]] = {
        key: Counter() for key in buckets
    }

    for observation, _states, pre, future in rows:
        if future is None:
            raise AssertionError("failure diagnostic requires future labels")
        history.append(observation)
        assessment = assess_global_opportunity(tuple(history), policy=policy)
        target = sti2._target_state(pre, future)
        future_material = max(
            target[CausalConcept.EXPANSION_READINESS],
            target[CausalConcept.DISPLACEMENT],
            target[CausalConcept.CONTINUATION],
            target[CausalConcept.REVERSAL],
        ) >= sti2.FUTURE_MATERIAL_TARGET_BPS
        alert = assessment.maturity in {
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.MATURE,
        }
        key = (
            "TP"
            if alert and future_material
            else "FP"
            if alert
            else "FN"
            if future_material
            else "TN"
        )
        buckets[key].append(
            {feature: int(getattr(observation, feature)) for feature in FEATURES}
        )
        maturity[key][assessment.maturity.value] += 1
        future_targets[key][_dominant_target(target)] += 1

    profiles = {key: _profile(value) for key, value in buckets.items()}
    return {
        "partition": partition,
        "sample_count": len(rows),
        "confusion_counts": {
            key: len(value) for key, value in buckets.items()
        },
        "source_feature_profiles_bps": profiles,
        "fn_minus_tn_source_feature_delta_bps": _delta(
            profiles["FN"],
            profiles["TN"],
        ),
        "tp_minus_fp_source_feature_delta_bps": _delta(
            profiles["TP"],
            profiles["FP"],
        ),
        "maturity_histograms": {
            key: dict(sorted(value.items()))
            for key, value in maturity.items()
        },
        "future_mechanism_histograms": {
            key: dict(sorted(value.items()))
            for key, value in future_targets.items()
        },
        "v2_hypothesis_candidates": _hypotheses(
            fn_profile=profiles["FN"],
            tn_profile=profiles["TN"],
            fn_maturity=maturity["FN"],
            fn_target=future_targets["FN"],
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--r5-nas", type=Path, required=True)
    parser.add_argument("--r5-sp", type=Path, required=True)
    parser.add_argument("--r5-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    frozen = cast(dict[str, Any], json.loads(args.policy.read_text()))
    result = {
        "identity": IDENTITY,
        "status": "V1_FAILURE_KNOWLEDGE_EXTRACTED_NO_RETUNING",
        "source_policy_fingerprint": frozen["policy"]["fingerprint"],
        "partitions": {
            "r6": diagnose_partition(
                partition="r6",
                paths={
                    "NAS100": args.r6_nas,
                    "SP500": args.r6_sp,
                    "US30": args.r6_us,
                },
                frozen=frozen,
            ),
            "r5": diagnose_partition(
                partition="r5",
                paths={
                    "NAS100": args.r5_nas,
                    "SP500": args.r5_sp,
                    "US30": args.r5_us,
                },
                frozen=frozen,
            ),
        },
        "governance": {
            "v1_policy_changed": False,
            "v1_thresholds_changed": False,
            "v1_reopened": False,
            "v2_policy_selected": False,
            "future_outcome_used_for_v1_decision": False,
            "consumed_evidence_only": True,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "status": result["status"],
                "r6_hypotheses": result["partitions"]["r6"][
                    "v2_hypothesis_candidates"
                ],
                "r5_hypotheses": result["partitions"]["r5"][
                    "v2_hypothesis_candidates"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
