#!/usr/bin/env python3
"""MC-14 latent temporal-causal consumed-evidence diagnostic.

The exact WP-04 V3 representation is rebuilt from already-consumed R8/R6/R5.
R8 latent activation quantiles are source-only threshold calibration. Candidate
relations are frozen on R8 and checked unchanged on later R6/R5. Because the
representation itself used these partitions for development/invariance, this
run is a consumed diagnostic only and cannot complete MC-14.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from shared_wp03_historical_causal_discovery import (
    TARGET_CONCEPTS,
    _prepare_partition,
)
from shared_wp04_invariant_representation_v2 import (
    PARTITIONS,
    _prepare_source_partition,
)
from shared_wp04_predictive_representation_v3 import POLICY, _build_transitions

from qore.infrastructure.core_stack_v2.representation_predictive_probe_v3 import (
    predictive_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    fit_predictive_representation,
    project_predictive_representation,
)
from qore.infrastructure.core_stack_v2.temporal_causal_latent_model import (
    TemporalCausalDisposition,
    TemporalCausalLatentRelation,
)

IDENTITY = "QORE_SHARED_MC14_LATENT_TEMPORAL_CAUSAL_DIAGNOSTIC_001"
EXPECTED_REPRESENTATION = (
    "e2fc2ca059d5852b4e9107c467392e5e64aeabbd6aca2d8013951b93402bc987"
)
MINIMUM_EFFECT_BPS = 500
MINIMUM_GROUP_COUNT = 250
MINIMUM_STRATUM_GROUP_COUNT = 20
MINIMUM_STABILITY_BPS = 8_000


def _percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires values")
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    weight = position - left
    return int(round(ordered[left] * (1.0 - weight) + ordered[right] * weight))


def _sign(value: int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _effect(
    rows: list[dict[str, object]],
    *,
    target_name: str,
    low: int,
    high: int,
) -> tuple[int | None, int, int]:
    exposed = [
        int(row["targets"][target_name])
        for row in rows
        if int(row["activation_milli_z"]) >= high
    ]
    controls = [
        int(row["targets"][target_name])
        for row in rows
        if int(row["activation_milli_z"]) <= low
    ]
    if (
        len(exposed) < MINIMUM_GROUP_COUNT
        or len(controls) < MINIMUM_GROUP_COUNT
    ):
        return None, len(exposed), len(controls)
    return int(round(mean(exposed) - mean(controls))), len(exposed), len(controls)


def _stability(
    rows: list[dict[str, object]],
    *,
    target_name: str,
    low: int,
    high: int,
    group_key: str,
    reference_effect: int,
) -> int:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[group_key])].append(row)

    effects: list[int] = []
    for group in grouped.values():
        exposed = [
            int(row["targets"][target_name])
            for row in group
            if int(row["activation_milli_z"]) >= high
        ]
        controls = [
            int(row["targets"][target_name])
            for row in group
            if int(row["activation_milli_z"]) <= low
        ]
        if (
            len(exposed) < MINIMUM_STRATUM_GROUP_COUNT
            or len(controls) < MINIMUM_STRATUM_GROUP_COUNT
        ):
            continue
        effects.append(int(round(mean(exposed) - mean(controls))))

    if not effects:
        return 0
    consistent = sum(
        abs(effect) >= MINIMUM_EFFECT_BPS
        and _sign(effect) == _sign(reference_effect)
        for effect in effects
    )
    return consistent * 10_000 // len(effects)


def _build_rows(
    *,
    partition: str,
    source_episodes,
    model,
    evidence_paths: dict[str, Path],
) -> dict[str, list[dict[str, object]]]:
    observations = _prepare_partition(
        partition=partition,
        evidence_paths=evidence_paths,
    )
    by_time = {item.source_at: item for item in observations}
    rows: dict[str, list[dict[str, object]]] = {
        concept.concept_id: [] for concept in model.concepts
    }
    for episode in source_episodes:
        observation = by_time.get(episode.as_of)
        if observation is None:
            continue
        latent = project_predictive_representation(model=model, episode=episode)
        targets = {
            concept.value: observation.target(concept)
            for concept in TARGET_CONCEPTS
        }
        for activation in latent.activations:
            rows[activation.concept_id].append(
                {
                    "activation_milli_z": activation.activation_milli_z,
                    "targets": targets,
                    "confounder_key": observation.confounder_key,
                    "regime_key": observation.regime_key,
                    "source_at": observation.source_at.isoformat(),
                    "target_at": observation.target_at.isoformat(),
                }
            )
    return rows


def _partition_metrics(
    rows: list[dict[str, object]],
    *,
    target_name: str,
    low: int,
    high: int,
    reference_sign: int | None = None,
) -> dict[str, object]:
    effect, exposed, control = _effect(
        rows,
        target_name=target_name,
        low=low,
        high=high,
    )
    if effect is None:
        return {
            "effect_bps": None,
            "exposed_count": exposed,
            "control_count": control,
            "conditional_sign_stability_bps": 0,
            "cross_regime_stability_bps": 0,
            "material_same_sign": False,
        }
    conditional = _stability(
        rows,
        target_name=target_name,
        low=low,
        high=high,
        group_key="confounder_key",
        reference_effect=effect,
    )
    regimes = _stability(
        rows,
        target_name=target_name,
        low=low,
        high=high,
        group_key="regime_key",
        reference_effect=effect,
    )
    material_same_sign = (
        abs(effect) >= MINIMUM_EFFECT_BPS
        and (
            reference_sign is None
            or _sign(effect) == reference_sign
        )
        and conditional >= MINIMUM_STABILITY_BPS
        and regimes >= MINIMUM_STABILITY_BPS
    )
    return {
        "effect_bps": effect,
        "exposed_count": exposed,
        "control_count": control,
        "conditional_sign_stability_bps": conditional,
        "cross_regime_stability_bps": regimes,
        "material_same_sign": material_same_sign,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in PARTITIONS:
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence = {
        partition: {
            "NAS100": getattr(args, f"{partition}_nas"),
            "SP500": getattr(args, f"{partition}_sp"),
            "US30": getattr(args, f"{partition}_us"),
        }
        for partition in PARTITIONS
    }

    source_episodes = {}
    transitions = {}
    for partition in PARTITIONS:
        episodes, _source_range = _prepare_source_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        source_episodes[partition] = episodes
        transitions[partition] = _build_transitions(episodes)

    fitted_at = max(
        item.future.as_of
        for partition_rows in transitions.values()
        for item in partition_rows
    )
    model = fit_predictive_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        transitions_by_partition=transitions,
        policy=POLICY,
    )
    fingerprint = predictive_representation_fingerprint(model)
    if fingerprint != EXPECTED_REPRESENTATION:
        raise ValueError("MC14 WP04 representation fingerprint drift")

    rows = {
        partition: _build_rows(
            partition=partition,
            source_episodes=source_episodes[partition],
            model=model,
            evidence_paths=evidence[partition],
        )
        for partition in PARTITIONS
    }

    relations = []
    candidates = 0
    consumed_replicated = 0
    falsified = 0
    for concept in model.concepts:
        concept_id = concept.concept_id
        r8_values = [
            int(row["activation_milli_z"])
            for row in rows["r8"][concept_id]
        ]
        low = _percentile(r8_values, 0.25)
        high = _percentile(r8_values, 0.75)
        if low >= high:
            continue

        for target in TARGET_CONCEPTS:
            target_name = target.value
            discovery = _partition_metrics(
                rows["r8"][concept_id],
                target_name=target_name,
                low=low,
                high=high,
            )
            effect = discovery["effect_bps"]
            is_candidate = (
                effect is not None
                and bool(discovery["material_same_sign"])
            )
            if not is_candidate:
                disposition = TemporalCausalDisposition.INSUFFICIENT
                if effect is None:
                    relation = TemporalCausalLatentRelation(
                        latent_concept_id=concept_id,
                        target_name=target_name,
                        disposition=disposition,
                        discovery_effect_bps=0,
                        r6_effect_bps=None,
                        r5_effect_bps=None,
                        discovery_sign_stability_bps=0,
                        r6_sign_stability_bps=None,
                        r5_sign_stability_bps=None,
                        discovery_regime_stability_bps=0,
                        r6_regime_stability_bps=None,
                        r5_regime_stability_bps=None,
                        source_threshold_low_milli_z=low,
                        source_threshold_high_milli_z=high,
                        evidence_refs=(
                            "artifact:10906064254",
                            "run:36236760353",
                        ),
                    )
                else:
                    relation = TemporalCausalLatentRelation(
                        latent_concept_id=concept_id,
                        target_name=target_name,
                        disposition=TemporalCausalDisposition.ASSOCIATION_ONLY,
                        discovery_effect_bps=int(effect),
                        r6_effect_bps=None,
                        r5_effect_bps=None,
                        discovery_sign_stability_bps=int(
                            discovery["conditional_sign_stability_bps"]
                        ),
                        r6_sign_stability_bps=None,
                        r5_sign_stability_bps=None,
                        discovery_regime_stability_bps=int(
                            discovery["cross_regime_stability_bps"]
                        ),
                        r6_regime_stability_bps=None,
                        r5_regime_stability_bps=None,
                        source_threshold_low_milli_z=low,
                        source_threshold_high_milli_z=high,
                        evidence_refs=(
                            "artifact:10906064254",
                            "run:36236760353",
                        ),
                    )
                relations.append(relation)
                continue

            candidates += 1
            reference_sign = _sign(int(effect))
            r6 = _partition_metrics(
                rows["r6"][concept_id],
                target_name=target_name,
                low=low,
                high=high,
                reference_sign=reference_sign,
            )
            r5 = _partition_metrics(
                rows["r5"][concept_id],
                target_name=target_name,
                low=low,
                high=high,
                reference_sign=reference_sign,
            )
            replicated = bool(
                r6["material_same_sign"] and r5["material_same_sign"]
            )
            disposition = (
                TemporalCausalDisposition.CONSUMED_TEMPORAL_REPLICATED
                if replicated
                else TemporalCausalDisposition.FALSIFIED
            )
            consumed_replicated += int(replicated)
            falsified += int(not replicated)
            relations.append(
                TemporalCausalLatentRelation(
                    latent_concept_id=concept_id,
                    target_name=target_name,
                    disposition=disposition,
                    discovery_effect_bps=int(effect),
                    r6_effect_bps=(
                        None
                        if r6["effect_bps"] is None
                        else int(r6["effect_bps"])
                    ),
                    r5_effect_bps=(
                        None
                        if r5["effect_bps"] is None
                        else int(r5["effect_bps"])
                    ),
                    discovery_sign_stability_bps=int(
                        discovery["conditional_sign_stability_bps"]
                    ),
                    r6_sign_stability_bps=int(
                        r6["conditional_sign_stability_bps"]
                    ),
                    r5_sign_stability_bps=int(
                        r5["conditional_sign_stability_bps"]
                    ),
                    discovery_regime_stability_bps=int(
                        discovery["cross_regime_stability_bps"]
                    ),
                    r6_regime_stability_bps=int(
                        r6["cross_regime_stability_bps"]
                    ),
                    r5_regime_stability_bps=int(
                        r5["cross_regime_stability_bps"]
                    ),
                    source_threshold_low_milli_z=low,
                    source_threshold_high_milli_z=high,
                    evidence_refs=(
                        "artifact:10906064254",
                        "run:36236760353",
                    ),
                )
            )

    payload = {
        "identity": IDENTITY,
        "status": "MC14_LATENT_TEMPORAL_CAUSAL_CONSUMED_DIAGNOSTIC_COMPLETE",
        "representation_fingerprint": fingerprint,
        "latent_concept_count": len(model.concepts),
        "target_count": len(TARGET_CONCEPTS),
        "relation_count": len(relations),
        "r8_research_candidate_count": candidates,
        "consumed_temporal_replicated_count": consumed_replicated,
        "falsified_candidate_count": falsified,
        "relations": [
            {
                "latent_concept_id": item.latent_concept_id,
                "target_name": item.target_name,
                "disposition": item.disposition.value,
                "discovery_effect_bps": item.discovery_effect_bps,
                "r6_effect_bps": item.r6_effect_bps,
                "r5_effect_bps": item.r5_effect_bps,
                "discovery_sign_stability_bps": (
                    item.discovery_sign_stability_bps
                ),
                "r6_sign_stability_bps": item.r6_sign_stability_bps,
                "r5_sign_stability_bps": item.r5_sign_stability_bps,
                "discovery_regime_stability_bps": (
                    item.discovery_regime_stability_bps
                ),
                "r6_regime_stability_bps": item.r6_regime_stability_bps,
                "r5_regime_stability_bps": item.r5_regime_stability_bps,
                "source_threshold_low_milli_z": (
                    item.source_threshold_low_milli_z
                ),
                "source_threshold_high_milli_z": (
                    item.source_threshold_high_milli_z
                ),
                "fingerprint": item.fingerprint(),
            }
            for item in relations
        ],
        "r8_source_thresholds_target_blind": True,
        "r6_r5_used_for_threshold_fit": False,
        "fresh_temporal_validation_used": False,
        "knowledge_auto_promotion": False,
        "mc14_completed_and_proven": False,
        "next_gate": (
            "FRESH_TEMPORAL_VALIDATION_OF_FROZEN_LATENT_CAUSAL_RELATIONS"
            if consumed_replicated > 0
            else "NEW_INFORMATION_OR_REPRESENTATION_REQUIRED"
        ),
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "candidate_count": candidates,
                "consumed_temporal_replicated_count": consumed_replicated,
                "falsified_candidate_count": falsified,
                "next_gate": payload["next_gate"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
