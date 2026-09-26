#!/usr/bin/env python3
"""Historical WP-04 representation discovery and frozen OOS evaluation.

Protocol is frozen before historical outcomes are inspected:
- R8: source-only representation discovery + consumed target probe fitting.
- R6: later out-of-sample evaluation with no refit.
- R5: still-later replication with no refit.
- Continuous market grid only; trader event timestamps are not used.
- Sequence features use generic PRIMARY / PEER_A / PEER_B roles rather than
  trader, setup or symbol identity fields.
- Existing Shared causal source concepts form the ontology baseline.
- Future 30-minute generic market-state concepts are evaluation labels only.

WP-04 passes only if ontology+latent representation reduces pooled MSE by at
least 1% (100 bps) in both R6 and R5 and improves at least half of the frozen
future-state probes in each partition.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import (
    MARKETS,
    PRE_WINDOW_MINUTES,
    SOURCE_CONCEPTS,
    TARGET_CONCEPTS,
    TARGET_HORIZON_MINUTES,
    _load_bars,
    _metric,
    _parse_key,
    _source_state,
    _target_state,
)

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationDiscoveryPolicy,
    RepresentationEpisode,
    RepresentationValue,
    fit_representation_discovery,
    project_representation,
)
from qore.infrastructure.core_stack_v2.representation_discovery_evaluation import (
    IncrementalRepresentationEvaluation,
    RepresentationEvaluationTarget,
    evaluate_incremental_representation,
    fit_incremental_representation_probe,
)

SCHEMA = "qore.shared.wp04.historical_representation_discovery.v1"
IDENTITY = "QORE_SHARED_WP04_HISTORICAL_REPRESENTATION_DISCOVERY_001"
PARTITIONS = ("r8", "r6", "r5")
SAMPLE_MINUTES = (0, 30)
ROLE_BY_MARKET = {
    "NAS100": "PRIMARY",
    "SP500": "PEER_A",
    "US30": "PEER_B",
}
HORIZONS = (5, 15, 30, 60)
MINIMUM_SAMPLES = 7_000
MINIMUM_OOS_INCREMENTAL_BPS = 100
MINIMUM_POSITIVE_TARGETS = (len(TARGET_CONCEPTS) + 1) // 2

DISCOVERY_POLICY = RepresentationDiscoveryPolicy(
    maximum_concepts=6,
    minimum_episode_count=MINIMUM_SAMPLES,
    minimum_integrity_bps=9_500,
    residualization_ridge=0.20,
    minimum_component_variance_bps=250,
    power_iterations=120,
    cluster_episode_count=12,
)


def _feature_values(
    windows: dict[str, tuple[Any, ...]],
) -> tuple[RepresentationValue, ...]:
    values: list[RepresentationValue] = []
    horizon_metrics: dict[int, dict[str, Any]] = {}
    for horizon in HORIZONS:
        horizon_metrics[horizon] = {}
        for market in MARKETS:
            metric = _metric(windows[market][-horizon:])
            horizon_metrics[horizon][market] = metric
            role = ROLE_BY_MARKET[market]
            values.extend(
                (
                    RepresentationValue(
                        f"{role}_NET_BPS_H{horizon}",
                        metric.net_bps,
                    ),
                    RepresentationValue(
                        f"{role}_PATH_BPS_H{horizon}",
                        metric.path_bps,
                    ),
                    RepresentationValue(
                        f"{role}_EFFICIENCY_H{horizon}",
                        metric.efficiency * 10_000.0,
                    ),
                    RepresentationValue(
                        f"{role}_RANGE_MEAN_BPS_H{horizon}",
                        metric.range_mean_bps,
                    ),
                    RepresentationValue(
                        f"{role}_MAX_ABS_RETURN_BPS_H{horizon}",
                        metric.max_abs_return_bps,
                    ),
                    RepresentationValue(
                        f"{role}_WICK_FRACTION_H{horizon}",
                        metric.wick_fraction * 10_000.0,
                    ),
                )
            )

        net = {
            market: horizon_metrics[horizon][market].net_bps
            for market in MARKETS
        }
        signs = [
            1 if net[market] > 0 else -1 if net[market] < 0 else 0
            for market in MARKETS
        ]
        coherence = abs(sum(signs) / len(signs)) * 10_000.0
        peer_mean = (net["SP500"] + net["US30"]) / 2.0
        dispersion = max(net.values()) - min(net.values())
        values.extend(
            (
                RepresentationValue(
                    f"CROSS_ROLE_COHERENCE_H{horizon}",
                    coherence,
                ),
                RepresentationValue(
                    f"PRIMARY_PEER_ROTATION_BPS_H{horizon}",
                    net["NAS100"] - peer_mean,
                ),
                RepresentationValue(
                    f"CROSS_ROLE_DISPERSION_BPS_H{horizon}",
                    dispersion,
                ),
            )
        )
    return tuple(values)


def _prepare_partition(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[
    tuple[RepresentationEpisode, ...],
    dict[str, tuple[RepresentationEvaluationTarget, ...]],
    dict[str, str | None],
]:
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
    targets: dict[str, list[RepresentationEvaluationTarget]] = {
        concept.value: []
        for concept in TARGET_CONCEPTS
    }

    nas = bars["NAS100"]
    for nas_index in range(
        PRE_WINDOW_MINUTES,
        len(nas) - TARGET_HORIZON_MINUTES - 1,
    ):
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
        future: dict[str, tuple[Any, ...]] = {}
        continuous = True
        for market in MARKETS:
            index = indexes[market]
            if (
                index < PRE_WINDOW_MINUTES
                or index + TARGET_HORIZON_MINUTES >= len(bars[market])
            ):
                continuous = False
                break
            pre_rows = bars[market][
                index - PRE_WINDOW_MINUTES + 1 : index + 1
            ]
            future_rows = bars[market][
                index + 1 : index + 1 + TARGET_HORIZON_MINUTES
            ]
            source_at = _parse_key(pre_rows[-1].closed_key)
            pre_start = _parse_key(pre_rows[-60].closed_key)
            target_at = _parse_key(future_rows[-1].closed_key)
            if (source_at - pre_start).total_seconds() > 70 * 60:
                continuous = False
                break
            if (target_at - source_at).total_seconds() > 35 * 60:
                continuous = False
                break
            pre[market] = pre_rows
            future[market] = future_rows
        if not continuous:
            continue

        source_at = _parse_key(pre["NAS100"][-1].closed_key)
        target_at = _parse_key(future["NAS100"][-1].closed_key)
        source_states, _vol_ratio, _coherence = _source_state(pre)
        target_states = _target_state(pre, future)
        episode_id = f"{partition}:{source_at.isoformat()}"

        episodes.append(
            RepresentationEpisode(
                episode_id=episode_id,
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
        for concept in TARGET_CONCEPTS:
            targets[concept.value].append(
                RepresentationEvaluationTarget(
                    episode_id=episode_id,
                    observed_at=target_at,
                    value=float(target_states[concept]),
                )
            )

    ranges = {
        "source_min": (
            min(item.as_of for item in episodes).isoformat()
            if episodes
            else None
        ),
        "source_max": (
            max(item.as_of for item in episodes).isoformat()
            if episodes
            else None
        ),
        "target_max": (
            max(
                item.observed_at
                for rows in targets.values()
                for item in rows
            ).isoformat()
            if episodes
            else None
        ),
    }
    del bars
    del peer_indexes
    gc.collect()
    return (
        tuple(episodes),
        {
            key: tuple(rows)
            for key, rows in targets.items()
        },
        ranges,
    )


def _evaluation_payload(
    evaluation: IncrementalRepresentationEvaluation,
) -> dict[str, int | str | bool]:
    return {
        "partition": evaluation.partition,
        "target_name": evaluation.target_name,
        "sample_count": evaluation.sample_count,
        "baseline_mse_micros": evaluation.baseline_mse_micros,
        "augmented_mse_micros": evaluation.augmented_mse_micros,
        "incremental_information_bps": (
            evaluation.incremental_information_bps
        ),
        "holdout_refit": evaluation.holdout_refit,
        "identity_used": evaluation.identity_used,
        "knowledge_promotion_authority": (
            evaluation.knowledge_promotion_authority
        ),
    }


def _partition_summary(
    evaluations: list[IncrementalRepresentationEvaluation],
) -> dict[str, Any]:
    if not evaluations:
        raise ValueError("partition summary requires evaluations")
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
        incremental >= MINIMUM_OOS_INCREMENTAL_BPS
        and positive >= MINIMUM_POSITIVE_TARGETS
    )
    return {
        "target_count": len(evaluations),
        "positive_target_count": positive,
        "minimum_positive_target_count": MINIMUM_POSITIVE_TARGETS,
        "pooled_baseline_mse_micros": int(round(baseline)),
        "pooled_augmented_mse_micros": int(round(augmented)),
        "pooled_incremental_information_bps": incremental,
        "minimum_incremental_information_bps": (
            MINIMUM_OOS_INCREMENTAL_BPS
        ),
        "pass": passed,
        "targets": [
            _evaluation_payload(item)
            for item in evaluations
        ],
    }


def _concept_payload(model: Any) -> list[dict[str, Any]]:
    return [
        {
            "concept_id": concept.concept_id,
            "explained_residual_variance_bps": (
                concept.explained_residual_variance_bps
            ),
            "positive_probe_features": list(
                concept.positive_probe_features
            ),
            "negative_probe_features": list(
                concept.negative_probe_features
            ),
            "positive_cluster_episode_ids": list(
                concept.positive_cluster_episode_ids
            ),
            "negative_cluster_episode_ids": list(
                concept.negative_cluster_episode_ids
            ),
        }
        for concept in model.concepts
    ]


def _activation_summary(
    *,
    model: Any,
    episodes: tuple[RepresentationEpisode, ...],
) -> dict[str, dict[str, int]]:
    values: dict[str, list[int]] = {
        concept.concept_id: []
        for concept in model.concepts
    }
    for episode in episodes:
        representation = project_representation(
            model=model,
            episode=episode,
        )
        for activation in representation.activations:
            values[activation.concept_id].append(
                activation.activation_milli_z
            )
    return {
        concept_id: {
            "count": len(rows),
            "minimum_milli_z": min(rows),
            "maximum_milli_z": max(rows),
            "mean_abs_milli_z": (
                sum(abs(value) for value in rows) // len(rows)
            ),
        }
        for concept_id, rows in values.items()
        if rows
    }


def run(
    *,
    evidence: dict[str, dict[str, Path]],
) -> dict[str, Any]:
    r8, r8_targets, r8_range = _prepare_partition(
        partition="r8",
        evidence_paths=evidence["r8"],
    )
    if len(r8) < MINIMUM_SAMPLES:
        raise ValueError("R8 does not meet WP04 minimum sample gate")

    model = fit_representation_discovery(
        fitted_at=max(item.as_of for item in r8),
        episodes=r8,
        policy=DISCOVERY_POLICY,
    )
    if not model.concepts:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP04_NO_RESIDUAL_CONCEPTS",
            "protocol_pass": False,
        }

    probe_fit_at = max(
        target.observed_at
        for rows in r8_targets.values()
        for target in rows
    )
    probes = {
        target_name: fit_incremental_representation_probe(
            model=model,
            fitted_at=probe_fit_at,
            calibration_partition="r8",
            target_name=target_name,
            episodes=r8,
            targets=r8_targets[target_name],
        )
        for target_name in sorted(r8_targets)
    }
    r8_activation = _activation_summary(model=model, episodes=r8)
    del r8
    del r8_targets
    gc.collect()

    r6, r6_targets, r6_range = _prepare_partition(
        partition="r6",
        evidence_paths=evidence["r6"],
    )
    r6_evaluations = [
        evaluate_incremental_representation(
            model=model,
            probe=probes[target_name],
            partition="r6",
            episodes=r6,
            targets=r6_targets[target_name],
        )
        for target_name in sorted(probes)
    ]
    r6_activation = _activation_summary(model=model, episodes=r6)
    r6_summary = _partition_summary(r6_evaluations)
    r6_count = len(r6)
    del r6
    del r6_targets
    gc.collect()

    r5, r5_targets, r5_range = _prepare_partition(
        partition="r5",
        evidence_paths=evidence["r5"],
    )
    r5_evaluations = [
        evaluate_incremental_representation(
            model=model,
            probe=probes[target_name],
            partition="r5",
            episodes=r5,
            targets=r5_targets[target_name],
        )
        for target_name in sorted(probes)
    ]
    r5_activation = _activation_summary(model=model, episodes=r5)
    r5_summary = _partition_summary(r5_evaluations)
    r5_count = len(r5)

    temporal_pass = bool(
        r8_range["target_max"]
        and r6_range["source_min"]
        and r6_range["target_max"]
        and r5_range["source_min"]
        and r8_range["target_max"] < r6_range["source_min"]
        and r6_range["target_max"] < r5_range["source_min"]
    )
    sample_pass = (
        model.episode_count >= MINIMUM_SAMPLES
        and r6_count >= MINIMUM_SAMPLES
        and r5_count >= MINIMUM_SAMPLES
    )
    activation_pass = all(
        summary
        and all(
            row["maximum_milli_z"] > row["minimum_milli_z"]
            for row in summary.values()
        )
        for summary in (r8_activation, r6_activation, r5_activation)
    )
    protocol_pass = (
        temporal_pass
        and sample_pass
        and activation_pass
        and model.target_used is False
        and model.future_market_used is False
        and model.trader_identity_used is False
        and model.knowledge_promotion_authority is False
        and model.execution_authority is False
    )
    exit_gate_pass = (
        protocol_pass
        and r6_summary["pass"]
        and r5_summary["pass"]
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP04_OOS_INCREMENTAL_INFORMATION_PASS"
            if exit_gate_pass
            else "WP04_OOS_INCREMENTAL_INFORMATION_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "exit_gate_pass": exit_gate_pass,
        "discovery": {
            "partition": model.discovery_partition,
            "episode_count": model.episode_count,
            "concept_count": len(model.concepts),
            "concepts": _concept_payload(model),
            "feature_count": len(model.feature_names),
            "ontology_count": len(model.ontology_names),
            "target_used": model.target_used,
            "future_market_used": model.future_market_used,
            "trader_identity_used": model.trader_identity_used,
        },
        "partition_ranges": {
            "r8": r8_range,
            "r6": r6_range,
            "r5": r5_range,
        },
        "activation_summary": {
            "r8": r8_activation,
            "r6": r6_activation,
            "r5": r5_activation,
        },
        "r6_holdout": r6_summary,
        "r5_replication": r5_summary,
        "governance": {
            "representation_fit_partition": "r8_only",
            "representation_target_blind": True,
            "probe_fit_partition": "r8_only",
            "r6_refit": False,
            "r5_refit": False,
            "trader_event_timestamps_used": False,
            "full_market_grid_sampling": True,
            "trade_direction_used": False,
            "trade_entry_used": False,
            "trade_stop_used": False,
            "trade_target_used": False,
            "trade_pnl_used": False,
            "trade_terminal_outcome_used": False,
            "symbol_identity_feature_used": False,
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
                "exit_gate_pass": payload.get("exit_gate_pass", False),
                "concept_count": payload.get("discovery", {}).get(
                    "concept_count",
                    0,
                ),
                "r6_incremental_bps": payload.get(
                    "r6_holdout",
                    {},
                ).get("pooled_incremental_information_bps"),
                "r5_incremental_bps": payload.get(
                    "r5_replication",
                    {},
                ).get("pooled_incremental_information_bps"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
