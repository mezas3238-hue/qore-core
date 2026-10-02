"""WP-04 V3 consumed-development temporal predictive representation lab.

R8/R6/R5 are already-consumed development evidence. This lab creates exact
30-minute source->future transitions from the generic Shared representation
surface and learns time-lagged residual concepts without named evaluation
targets, trade outcomes, PnL, symbol identity or trader identity.

This lab is research-only. It cannot close WP-04 and cannot open a fresh
holdout. A surviving representation must still pass consumed incremental-
information diagnostics, be frozen, then face an independent one-shot holdout.
"""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from shared_wp04_invariant_representation_v2 import (
    PARTITIONS,
    _prepare_source_partition,
)

from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    PredictiveRepresentationPolicy,
    PredictiveTransitionEpisode,
    fit_predictive_representation,
)

SCHEMA = "qore.shared.wp04.predictive_representation_v3_development.v1"
IDENTITY = "QORE_SHARED_WP04_PREDICTIVE_REPRESENTATION_V3_DEVELOPMENT_001"
HORIZON_MINUTES = 30
MINIMUM_TRANSITIONS = 6_000

POLICY = PredictiveRepresentationPolicy(
    maximum_concepts=6,
    candidate_multiplier=4,
    minimum_transition_count_per_partition=MINIMUM_TRANSITIONS,
    minimum_integrity_bps=9_500,
    robust_width=3.0,
    residualization_ridge=0.20,
    minimum_predictive_strength_bps=25,
    power_iterations=120,
    minimum_future_profile_alignment_bps=7_500,
    minimum_predictive_strength_ratio=0.50,
    maximum_predictive_strength_ratio=2.00,
    minimum_source_scale_ratio=0.50,
    maximum_source_scale_ratio=2.00,
    maximum_source_median_shift_scale=1.50,
    cluster_episode_count=12,
)


def _build_transitions(
    episodes: tuple[Any, ...],
) -> tuple[PredictiveTransitionEpisode, ...]:
    by_time = {item.as_of: item for item in episodes}
    if len(by_time) != len(episodes):
        raise ValueError("source episode timestamps must be unique")
    delta = timedelta(minutes=HORIZON_MINUTES)
    rows: list[PredictiveTransitionEpisode] = []
    for source in episodes:
        future = by_time.get(source.as_of + delta)
        if future is None:
            continue
        rows.append(
            PredictiveTransitionEpisode(
                source=source,
                future=future,
                horizon_minutes=HORIZON_MINUTES,
            )
        )
    return tuple(rows)


def _concept_payload(model: Any) -> list[dict[str, Any]]:
    return [
        {
            "concept_id": concept.concept_id,
            "discovery_predictive_strength_bps": (
                concept.discovery_predictive_strength_bps
            ),
            "temporal_invariance_bps": concept.temporal_invariance_bps,
            "positive_probe_features": list(concept.positive_probe_features),
            "negative_probe_features": list(concept.negative_probe_features),
            "positive_cluster_episode_ids": list(
                concept.positive_cluster_episode_ids
            ),
            "negative_cluster_episode_ids": list(
                concept.negative_cluster_episode_ids
            ),
            "diagnostics": [
                {
                    "partition": diagnostic.partition,
                    "transition_count": diagnostic.transition_count,
                    "future_profile_alignment_bps": (
                        diagnostic.future_profile_alignment_bps
                    ),
                    "predictive_strength_ratio_milli": (
                        diagnostic.predictive_strength_ratio_milli
                    ),
                    "predictive_strength_stability_bps": (
                        diagnostic.predictive_strength_stability_bps
                    ),
                    "source_scale_ratio_milli": (
                        diagnostic.source_scale_ratio_milli
                    ),
                    "source_scale_stability_bps": (
                        diagnostic.source_scale_stability_bps
                    ),
                    "source_median_shift_milli_scale": (
                        diagnostic.source_median_shift_milli_scale
                    ),
                    "source_median_stability_bps": (
                        diagnostic.source_median_stability_bps
                    ),
                    "passes": diagnostic.passes,
                }
                for diagnostic in concept.diagnostics
            ],
        }
        for concept in model.concepts
    ]


def run(
    *,
    evidence: dict[str, dict[str, Path]],
) -> dict[str, Any]:
    source_partitions: dict[str, tuple[Any, ...]] = {}
    source_ranges: dict[str, dict[str, str | None]] = {}
    transitions: dict[str, tuple[PredictiveTransitionEpisode, ...]] = {}

    for partition in PARTITIONS:
        episodes, source_range = _prepare_source_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        source_partitions[partition] = episodes
        source_ranges[partition] = source_range
        transitions[partition] = _build_transitions(episodes)

    transition_counts = {
        partition: len(transitions[partition])
        for partition in PARTITIONS
    }
    sample_gate = all(
        transition_counts[partition] >= MINIMUM_TRANSITIONS
        for partition in PARTITIONS
    )
    if not sample_gate:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP04_V3_TRANSITION_SAMPLE_GATE_FAILED",
            "protocol_pass": False,
            "representation_frozen_for_probe": False,
            "fresh_holdout_opened": False,
            "transition_counts": transition_counts,
            "source_ranges": source_ranges,
        }

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
    concepts = _concept_payload(model)

    protocol_pass = (
        sample_gate
        and model.training_future_market_used is True
        and model.runtime_future_market_used is False
        and model.named_evaluation_target_used is False
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
            diagnostic["passes"]
            for concept in concepts
            for diagnostic in concept["diagnostics"]
        )
    )
    representation_frozen = protocol_pass and bool(concepts)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP04_V3_TEMPORAL_REPRESENTATION_FROZEN_FOR_PROBE"
            if representation_frozen
            else "WP04_V3_TEMPORAL_REPRESENTATION_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "representation_frozen_for_probe": representation_frozen,
        "exit_gate_pass": False,
        "fresh_holdout_opened": False,
        "source_episode_counts": {
            partition: len(source_partitions[partition])
            for partition in PARTITIONS
        },
        "transition_counts": transition_counts,
        "source_ranges": source_ranges,
        "model": {
            "horizon_minutes": model.horizon_minutes,
            "discovery_partition": model.discovery_partition,
            "development_partitions": list(model.development_partitions),
            "evidence_cutoff_at": model.evidence_cutoff_at.isoformat(),
            "feature_count": len(model.feature_names),
            "ontology_count": len(model.ontology_names),
            "candidate_count": model.candidate_count,
            "selected_concept_count": len(model.concepts),
            "rejected_candidate_count": model.rejected_candidate_count,
            "concepts": concepts,
            "training_future_market_used": model.training_future_market_used,
            "runtime_future_market_used": model.runtime_future_market_used,
            "named_evaluation_target_used": (
                model.named_evaluation_target_used
            ),
        },
        "frozen_policy": {
            "horizon_minutes": HORIZON_MINUTES,
            "maximum_concepts": POLICY.maximum_concepts,
            "candidate_multiplier": POLICY.candidate_multiplier,
            "minimum_predictive_strength_bps": (
                POLICY.minimum_predictive_strength_bps
            ),
            "minimum_future_profile_alignment_bps": (
                POLICY.minimum_future_profile_alignment_bps
            ),
            "minimum_predictive_strength_ratio": (
                POLICY.minimum_predictive_strength_ratio
            ),
            "maximum_predictive_strength_ratio": (
                POLICY.maximum_predictive_strength_ratio
            ),
            "minimum_source_scale_ratio": POLICY.minimum_source_scale_ratio,
            "maximum_source_scale_ratio": POLICY.maximum_source_scale_ratio,
            "maximum_source_median_shift_scale": (
                POLICY.maximum_source_median_shift_scale
            ),
            "robust_width": POLICY.robust_width,
            "residualization_ridge": POLICY.residualization_ridge,
        },
        "governance": {
            "r8_r6_r5_are_consumed_development": True,
            "future_state_prediction_training_only": True,
            "runtime_future_market_used": False,
            "named_evaluation_targets_used_for_discovery": False,
            "trade_outcomes_used": False,
            "trade_pnl_used": False,
            "symbol_identity_feature_used": False,
            "partition_identity_feature_used": False,
            "fresh_holdout_opened": False,
            "fresh_holdout_required_after_probe_freeze": True,
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
                "representation_frozen_for_probe": payload.get(
                    "representation_frozen_for_probe",
                    False,
                ),
                "transition_counts": payload.get("transition_counts", {}),
                "candidate_count": payload.get("model", {}).get(
                    "candidate_count",
                    0,
                ),
                "selected_concept_count": payload.get("model", {}).get(
                    "selected_concept_count",
                    0,
                ),
                "rejected_candidate_count": payload.get("model", {}).get(
                    "rejected_candidate_count",
                    0,
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
