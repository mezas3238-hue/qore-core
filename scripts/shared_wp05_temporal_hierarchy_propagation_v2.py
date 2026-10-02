"""WP-05 V2 consumed-development hierarchy propagation falsification.

V2 keeps the same scientific task and frozen gate as V1, but replaces the
single-snapshot readout with a source-only trajectory:
    t-60m -> t-30m -> t

It asks whether lower-timeframe opposition remains contained or propagates
upward while higher-timeframe resilience erodes.

R8 fits the generative terminal/recovery path prototypes and declaration
threshold. R6/R5 are consumed later falsification partitions only. No fresh
holdout is opened by this lab.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import (
    MARKETS,
    SAMPLE_MINUTES,
    TARGET_HORIZON_MINUTES,
    _load_bars,
    _parse_key,
)
from shared_wp05_temporal_hierarchy_v1 import (
    MAX_LOOKBACK,
    MINIMUM_BASELINE_TERMINALS,
    MINIMUM_EPISODES,
    MINIMUM_FALSE_REDUCTION_BPS,
    MINIMUM_TERMINAL_PRESERVATION_BPS,
    PARTITIONS,
    SCALE_HORIZONS,
    _scale_state,
    _terminal_failure,
)

from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
    TemporalHierarchyTrajectoryTrainingEpisode,
    TemporalHierarchyTransitionEvaluation,
    evaluate_temporal_hierarchy_transition,
    fit_temporal_hierarchy_transition_model,
)

SCHEMA = "qore.shared.wp05.temporal_hierarchy_propagation_consumed_v2"
IDENTITY = "QORE_SHARED_WP05_TEMPORAL_HIERARCHY_PROPAGATION_V2_001"
TRAJECTORY_OFFSETS_MINUTES = (60, 30, 0)
MAX_SEQUENCE_LOOKBACK = MAX_LOOKBACK + max(TRAJECTORY_OFFSETS_MINUTES)


def _prepare_partition(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[
    tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
    dict[str, str | int | None],
]:
    bars = {market: _load_bars(evidence_paths[market]) for market in MARKETS}
    peer_indexes = {
        market: {bar.closed_key: index for index, bar in enumerate(bars[market])}
        for market in ("SP500", "US30")
    }

    episodes: list[TemporalHierarchyTrajectoryTrainingEpisode] = []
    snapshot_cache: dict[
        tuple[int, int, int],
        TemporalHierarchySnapshot,
    ] = {}
    nas = bars["NAS100"]
    for nas_index in range(
        MAX_SEQUENCE_LOOKBACK,
        len(nas) - TARGET_HORIZON_MINUTES - 1,
    ):
        key = nas[nas_index].closed_key
        if int(key[14:16]) not in SAMPLE_MINUTES:
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

        current_pre: dict[str, tuple[Any, ...]] = {}
        future: dict[str, tuple[Any, ...]] = {}
        snapshots: list[TemporalHierarchySnapshot] = []
        valid = True
        snapshot_times = []

        for offset in TRAJECTORY_OFFSETS_MINUTES:
            end_indexes = {
                market: indexes[market] - offset
                for market in MARKETS
            }
            if any(
                end_index < MAX_LOOKBACK - 1
                for end_index in end_indexes.values()
            ):
                valid = False
                break

            cache_key = tuple(end_indexes[market] for market in MARKETS)
            cached = snapshot_cache.get(cache_key)
            windows: dict[str, tuple[Any, ...]] | None = None

            # Current pre-window is still required for the independently matured
            # terminal label. Historical trajectory states can reuse an exactly
            # identical source snapshot calculated by a neighboring grid point.
            if cached is None or offset == 0:
                windows = {}
                for market in MARKETS:
                    end_index = end_indexes[market]
                    rows = tuple(
                        bars[market][
                            end_index - MAX_LOOKBACK + 1 : end_index + 1
                        ]
                    )
                    if len(rows) != MAX_LOOKBACK:
                        valid = False
                        break
                    windows[market] = rows
                if not valid:
                    break

            if cached is None:
                if windows is None:
                    raise AssertionError("uncached hierarchy state needs windows")
                source_at = _parse_key(windows["NAS100"][-1].closed_key)
                levels = tuple(
                    _scale_state(
                        scale=scale,
                        horizon=horizon,
                        windows=windows,
                    )
                    for scale, horizon in SCALE_HORIZONS
                )
                cached = TemporalHierarchySnapshot(
                    episode_id=f"{partition}:{source_at.isoformat()}:state",
                    as_of=source_at,
                    levels=levels,
                )
                snapshot_cache[cache_key] = cached

            snapshots.append(cached)
            snapshot_times.append(cached.as_of)
            if offset == 0:
                if windows is None:
                    raise AssertionError("current hierarchy state needs pre-window")
                current_pre = windows

        if not valid or len(snapshots) != len(TRAJECTORY_OFFSETS_MINUTES):
            continue

        gaps = [
            (right - left).total_seconds() / 60.0
            for left, right in zip(snapshot_times, snapshot_times[1:], strict=False)
        ]
        if any(gap < 25 or gap > 40 for gap in gaps):
            continue

        for market in MARKETS:
            index = indexes[market]
            if index + TARGET_HORIZON_MINUTES >= len(bars[market]):
                valid = False
                break
            rows = tuple(
                bars[market][
                    index + 1 : index + 1 + TARGET_HORIZON_MINUTES
                ]
            )
            if len(rows) != TARGET_HORIZON_MINUTES:
                valid = False
                break
            future[market] = rows
        if not valid:
            continue

        source_at = snapshots[-1].as_of
        observed_at = _parse_key(future["NAS100"][-1].closed_key)
        if observed_at <= source_at:
            continue
        if (observed_at - source_at).total_seconds() > 35 * 60:
            continue

        trajectory = TemporalHierarchyTrajectory(
            episode_id=f"{partition}:{source_at.isoformat()}",
            snapshots=tuple(snapshots),
        )
        episodes.append(
            TemporalHierarchyTrajectoryTrainingEpisode(
                trajectory=trajectory,
                observed_at=observed_at,
                terminal_failure=_terminal_failure(
                    pre=current_pre,
                    future=future,
                ),
            )
        )

    del bars
    del peer_indexes
    del snapshot_cache
    gc.collect()

    return tuple(episodes), {
        "episode_count": len(episodes),
        "source_min": (
            min(item.trajectory.snapshots[-1].as_of for item in episodes).isoformat()
            if episodes
            else None
        ),
        "source_max": (
            max(item.trajectory.snapshots[-1].as_of for item in episodes).isoformat()
            if episodes
            else None
        ),
        "target_max": (
            max(item.observed_at for item in episodes).isoformat()
            if episodes
            else None
        ),
    }

def _evaluation_payload(
    evaluation: TemporalHierarchyTransitionEvaluation,
) -> dict[str, int | str]:
    return {
        "partition": evaluation.partition,
        "sample_count": evaluation.sample_count,
        "baseline_declaration_count": evaluation.baseline_declaration_count,
        "baseline_terminal_count": evaluation.baseline_terminal_count,
        "baseline_false_declaration_count": (
            evaluation.baseline_false_declaration_count
        ),
        "hierarchy_declaration_count": evaluation.hierarchy_declaration_count,
        "hierarchy_terminal_count": evaluation.hierarchy_terminal_count,
        "hierarchy_false_declaration_count": (
            evaluation.hierarchy_false_declaration_count
        ),
        "hierarchy_missed_terminal_count": (
            evaluation.hierarchy_missed_terminal_count
        ),
        "false_declaration_reduction_bps": (
            evaluation.false_declaration_reduction_bps
        ),
        "terminal_detection_preservation_bps": (
            evaluation.terminal_detection_preservation_bps
        ),
    }


def run(
    *,
    evidence: dict[str, dict[str, Path]],
) -> dict[str, Any]:
    partitions: dict[
        str,
        tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
    ] = {}
    ranges: dict[str, dict[str, str | int | None]] = {}

    for partition in PARTITIONS:
        rows, partition_range = _prepare_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        partitions[partition] = rows
        ranges[partition] = partition_range

    sample_gate = all(
        len(partitions[partition]) >= MINIMUM_EPISODES
        for partition in PARTITIONS
    )
    if not sample_gate:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP05_V2_SAMPLE_GATE_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "partition_ranges": ranges,
        }

    fitted_at = max(item.observed_at for item in partitions["r8"])
    model = fit_temporal_hierarchy_transition_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=partitions["r8"],
        minimum_training_recall_bps=MINIMUM_TERMINAL_PRESERVATION_BPS,
    )
    evaluations = {
        partition: evaluate_temporal_hierarchy_transition(
            model=model,
            partition=partition,
            episodes=partitions[partition],
        )
        for partition in PARTITIONS
    }

    development_gate_pass = all(
        evaluations[partition].baseline_terminal_count
        >= MINIMUM_BASELINE_TERMINALS
        and evaluations[partition].false_declaration_reduction_bps
        >= MINIMUM_FALSE_REDUCTION_BPS
        and evaluations[partition].terminal_detection_preservation_bps
        >= MINIMUM_TERMINAL_PRESERVATION_BPS
        for partition in ("r6", "r5")
    )

    protocol_pass = (
        sample_gate
        and model.target_used_for_training_only is True
        and model.runtime_future_market_used is False
        and model.outcome_used_at_runtime is False
        and model.trader_identity_used is False
        and model.symbol_identity_used is False
        and model.methodology_authority is False
        and model.knowledge_promotion_authority is False
        and model.sizing_authority is False
        and model.risk_authority is False
        and model.order_authority is False
        and model.execution_authority is False
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP05_V2_PROPAGATION_MODEL_FROZEN_FOR_FRESH_HOLDOUT"
            if protocol_pass and development_gate_pass
            else "WP05_V2_PROPAGATION_MODEL_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "development_gate_pass": development_gate_pass,
        "fresh_holdout_opened": False,
        "wp05_exit_gate_pass": False,
        "partition_ranges": ranges,
        "trajectory_offsets_minutes": list(TRAJECTORY_OFFSETS_MINUTES),
        "scale_horizons_m1_bars": {
            scale.value: horizon for scale, horizon in SCALE_HORIZONS
        },
        "model": {
            "fit_partition": model.fit_partition,
            "fitted_at": model.fitted_at.isoformat(),
            "feature_names": list(model.feature_names),
            "terminal_means_micros": list(model.terminal_means_micros),
            "terminal_scales_micros": list(model.terminal_scales_micros),
            "recovery_means_micros": list(model.recovery_means_micros),
            "recovery_scales_micros": list(model.recovery_scales_micros),
            "terminal_prior_micros": model.terminal_prior_micros,
            "declaration_threshold_micros": (
                model.declaration_threshold_micros
            ),
            "minimum_training_recall_bps": (
                model.minimum_training_recall_bps
            ),
            "threshold_calibration_recall_bps": (
                model.threshold_calibration_recall_bps
            ),
            "fit_opposition_count": model.fit_opposition_count,
            "fit_terminal_count": model.fit_terminal_count,
        },
        "evaluations": {
            partition: _evaluation_payload(evaluation)
            for partition, evaluation in evaluations.items()
        },
        "frozen_development_gate": {
            "minimum_false_declaration_reduction_bps": (
                MINIMUM_FALSE_REDUCTION_BPS
            ),
            "minimum_terminal_detection_preservation_bps": (
                MINIMUM_TERMINAL_PRESERVATION_BPS
            ),
            "minimum_baseline_terminal_count": (
                MINIMUM_BASELINE_TERMINALS
            ),
            "must_pass_partitions": ["r6", "r5"],
        },
        "governance": {
            "v1_gate_unchanged": True,
            "r8_fit_only": True,
            "r6_refit": False,
            "r5_refit": False,
            "threshold_fit_partition": "r8_only",
            "r6_threshold_retuning": False,
            "r5_threshold_retuning": False,
            "trajectory_source_only": True,
            "future_target_used_for_training_or_evaluation_only": True,
            "runtime_future_market_used": False,
            "trade_direction_used": False,
            "trade_entry_used": False,
            "trade_stop_used": False,
            "trade_target_used": False,
            "trade_pnl_used": False,
            "trader_identity_feature_used": False,
            "symbol_identity_feature_used": False,
            "fresh_holdout_opened": False,
            "fresh_holdout_required_before_wp05_exit": True,
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


def _paths(args: argparse.Namespace, partition: str) -> dict[str, Path]:
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
                "development_gate_pass": payload["development_gate_pass"],
                "evaluations": payload.get("evaluations", {}),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
