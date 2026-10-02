"""WP-04 V2 consumed-development source-invariance laboratory.

This laboratory does not open a fresh holdout and does not use future targets.
R8 supplies discovery geometry. R6 and R5 are already-consumed source-only
development partitions used exclusively to reject partition-specific residual
modes before any incremental-information probe is fitted.

The lab surface is role-based (PRIMARY / PEER_A / PEER_B) and exists only as a
falsification surface for generic Shared representation. It is not global QORE
completion and it cannot promote knowledge or authorize runtime behavior.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import (
    MARKETS,
    PRE_WINDOW_MINUTES,
    SOURCE_CONCEPTS,
    _load_bars,
    _parse_key,
    _source_state,
)
from shared_wp04_historical_representation_discovery import (
    SAMPLE_MINUTES,
    _feature_values,
)

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationEpisode,
    RepresentationValue,
)
from qore.infrastructure.core_stack_v2.representation_invariance_v2 import (
    InvariantRepresentationPolicy,
    fit_invariant_representation,
)

SCHEMA = "qore.shared.wp04.invariant_representation_v2_development.v1"
IDENTITY = "QORE_SHARED_WP04_INVARIANT_REPRESENTATION_V2_DEVELOPMENT_001"
PARTITIONS = ("r8", "r6", "r5")
MINIMUM_SAMPLES = 7_000

POLICY = InvariantRepresentationPolicy(
    maximum_concepts=6,
    candidate_multiplier=4,
    minimum_episode_count_per_partition=MINIMUM_SAMPLES,
    minimum_integrity_bps=9_500,
    robust_width=3.0,
    residualization_ridge=0.20,
    minimum_candidate_variance_bps=50,
    power_iterations=120,
    minimum_loading_alignment_bps=7_000,
    minimum_scale_ratio=0.50,
    maximum_scale_ratio=2.00,
    maximum_median_shift_scale=1.50,
    cluster_episode_count=12,
)


def _prepare_source_partition(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[tuple[RepresentationEpisode, ...], dict[str, str | None]]:
    bars = {
        market: _load_bars(evidence_paths[market])
        for market in MARKETS
    }
    peer_indexes = {
        market: {
            bar.closed_key: index
            for index, bar in enumerate(bars[market])
        }
        for market in ("SP500", "US30")
    }

    episodes: list[RepresentationEpisode] = []
    nas = bars["NAS100"]
    for nas_index in range(PRE_WINDOW_MINUTES, len(nas)):
        key = nas[nas_index].closed_key
        minute = int(key[14:16])
        if minute not in SAMPLE_MINUTES:
            continue

        indexes = {"NAS100": nas_index}
        missing = False
        for market in ("SP500", "US30"):
            peer_index = peer_indexes[market].get(key)
            if peer_index is None:
                missing = True
                break
            indexes[market] = peer_index
        if missing:
            continue

        pre: dict[str, tuple[Any, ...]] = {}
        continuous = True
        for market in MARKETS:
            index = indexes[market]
            if index < PRE_WINDOW_MINUTES:
                continuous = False
                break
            pre_rows = bars[market][
                index - PRE_WINDOW_MINUTES + 1 : index + 1
            ]
            source_at = _parse_key(pre_rows[-1].closed_key)
            pre_start = _parse_key(pre_rows[-60].closed_key)
            if (source_at - pre_start).total_seconds() > 70 * 60:
                continuous = False
                break
            pre[market] = pre_rows
        if not continuous:
            continue

        source_at = _parse_key(pre["NAS100"][-1].closed_key)
        source_states, _vol_ratio, _coherence = _source_state(pre)
        episodes.append(
            RepresentationEpisode(
                episode_id=f"{partition}:{source_at.isoformat()}",
                as_of=source_at,
                partition=partition,
                features=_feature_values(pre),
                ontology=tuple(
                    RepresentationValue(
                        f"ONTOLOGY_{concept.value}",
                        float(source_states[concept]),
                    )
                    for concept in SOURCE_CONCEPTS
                ),
                integrity_bps=10_000,
            )
        )

    if not episodes:
        return (), {"source_min": None, "source_max": None}
    return tuple(episodes), {
        "source_min": min(item.as_of for item in episodes).isoformat(),
        "source_max": max(item.as_of for item in episodes).isoformat(),
    }


def _concept_payload(model: Any) -> list[dict[str, Any]]:
    return [
        {
            "concept_id": concept.concept_id,
            "discovery_explained_residual_variance_bps": (
                concept.discovery_explained_residual_variance_bps
            ),
            "source_invariance_bps": concept.source_invariance_bps,
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
                    "episode_count": diagnostic.episode_count,
                    "loading_alignment_bps": (
                        diagnostic.loading_alignment_bps
                    ),
                    "activation_scale_ratio_milli": (
                        diagnostic.activation_scale_ratio_milli
                    ),
                    "activation_median_shift_milli_scale": (
                        diagnostic.activation_median_shift_milli_scale
                    ),
                    "scale_stability_bps": diagnostic.scale_stability_bps,
                    "median_stability_bps": diagnostic.median_stability_bps,
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
    prepared: dict[str, tuple[RepresentationEpisode, ...]] = {}
    ranges: dict[str, dict[str, str | None]] = {}
    for partition in PARTITIONS:
        rows, source_range = _prepare_source_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        prepared[partition] = rows
        ranges[partition] = source_range

    sample_gate = all(
        len(prepared[partition]) >= MINIMUM_SAMPLES
        for partition in PARTITIONS
    )
    if not sample_gate:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP04_V2_SOURCE_SAMPLE_GATE_FAILED",
            "protocol_pass": False,
            "source_episode_counts": {
                partition: len(prepared[partition])
                for partition in PARTITIONS
            },
            "source_ranges": ranges,
        }

    fitted_at = max(
        item.as_of
        for rows in prepared.values()
        for item in rows
    )
    model = fit_invariant_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        episodes_by_partition=prepared,
        policy=POLICY,
    )

    concepts = _concept_payload(model)
    protocol_pass = (
        sample_gate
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
            "WP04_V2_SOURCE_INVARIANCE_FROZEN_FOR_PROBE"
            if representation_frozen
            else "WP04_V2_SOURCE_INVARIANCE_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "representation_frozen_for_probe": representation_frozen,
        "exit_gate_pass": False,
        "source_episode_counts": {
            partition: len(prepared[partition])
            for partition in PARTITIONS
        },
        "source_ranges": ranges,
        "model": {
            "discovery_partition": model.discovery_partition,
            "development_partitions": list(model.development_partitions),
            "evidence_cutoff_at": model.evidence_cutoff_at.isoformat(),
            "feature_count": len(model.feature_names),
            "ontology_count": len(model.ontology_names),
            "candidate_count": model.candidate_count,
            "selected_concept_count": len(model.concepts),
            "rejected_candidate_count": model.rejected_candidate_count,
            "concepts": concepts,
        },
        "frozen_policy": {
            "maximum_concepts": POLICY.maximum_concepts,
            "candidate_multiplier": POLICY.candidate_multiplier,
            "minimum_candidate_variance_bps": (
                POLICY.minimum_candidate_variance_bps
            ),
            "minimum_loading_alignment_bps": (
                POLICY.minimum_loading_alignment_bps
            ),
            "minimum_scale_ratio": POLICY.minimum_scale_ratio,
            "maximum_scale_ratio": POLICY.maximum_scale_ratio,
            "maximum_median_shift_scale": (
                POLICY.maximum_median_shift_scale
            ),
            "robust_width": POLICY.robust_width,
            "residualization_ridge": POLICY.residualization_ridge,
        },
        "governance": {
            "development_evidence_consumed": True,
            "r8_role": "SOURCE_ONLY_DISCOVERY",
            "r6_role": "SOURCE_ONLY_INVARIANCE_DEVELOPMENT",
            "r5_role": "SOURCE_ONLY_INVARIANCE_DEVELOPMENT",
            "future_target_labels_used": False,
            "trade_outcomes_used": False,
            "trade_pnl_used": False,
            "symbol_identity_feature_used": False,
            "partition_identity_feature_used": False,
            "target_aware_component_selection": False,
            "fresh_holdout_opened": False,
            "fresh_holdout_required_after_probe_freeze": True,
            "global_qore_validation_still_required": True,
            "lab_surface_only_not_global_completion": True,
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
