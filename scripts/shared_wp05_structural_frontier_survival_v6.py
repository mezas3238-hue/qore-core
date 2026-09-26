"""WP-05 V6 structural-frontier survival consumed-development experiment.

Target V2 defines failure relative to the source-time higher-timeframe anchor
and a 20-minute structural frontier. V6 models that same source geometry:
distance to the frontier, approach velocity, rejection/recovery, local adverse
persistence, volatility, cross-market confirmation and multi-scale resilience.

R8 is the only fit/calibration partition. R6/R5 are consumed falsification
only. No fresh holdout is opened here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import fmean
from typing import Any

from shared_wp03_historical_causal_discovery import MARKETS, _load_bars
from shared_wp05_structural_failure_target_v2 import (
    relabel_partition_with_structural_failure_v2,
)
from shared_wp05_temporal_hierarchy_absorption_v3 import (
    PARTITIONS,
    _paths,
)
from shared_wp05_temporal_hierarchy_v1 import (
    MINIMUM_BASELINE_TERMINALS,
    MINIMUM_EPISODES,
    MINIMUM_FALSE_REDUCTION_BPS,
    MINIMUM_TERMINAL_PRESERVATION_BPS,
)

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    baseline_local_opposition,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_structural_frontier_v6 import (
    StructuralFrontierEvaluation,
    StructuralFrontierSourceState,
    StructuralFrontierTrainingEpisode,
    evaluate_structural_frontier,
    fit_structural_frontier_model,
    structural_frontier_hierarchy_motif,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_target_contract import (
    higher_timeframe_anchor_direction,
)

SCHEMA = "qore.shared.wp05.structural_frontier_survival_consumed.v6"
IDENTITY = "QORE_SHARED_WP05_STRUCTURAL_FRONTIER_SURVIVAL_V6_001"
TARGET_CONTRACT = "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2"


def _return_bps(last: float, first: float) -> float:
    if first == 0:
        return 0.0
    return (last / first - 1.0) * 10_000.0


def _scale_map(snapshot: TemporalHierarchySnapshot) -> dict[WorldScale, Any]:
    return {item.scale: item for item in snapshot.levels}


def _higher_resilience_minus_fragility(
    snapshot: TemporalHierarchySnapshot,
) -> float:
    levels = _scale_map(snapshot)
    rows = [
        levels[scale]
        for scale in (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
        if scale in levels
    ]
    if not rows:
        return 0.0
    return fmean(
        (
            item.persistence_bps
            + item.coherence_bps
            - item.fragility_bps
            - item.transition_bps
        )
        / 20_000.0
        for item in rows
    )


def _source_key(item: Any) -> str:
    return item.trajectory.snapshots[-1].as_of.strftime("%Y-%m-%dT%H:%M:%S")


def _build_source_state(
    *,
    item: Any,
    bars: dict[str, tuple[Any, ...]],
    indexes: dict[str, dict[str, int]],
) -> StructuralFrontierSourceState:
    snapshot = item.trajectory.snapshots[-1]
    anchor = higher_timeframe_anchor_direction(snapshot)
    if anchor == 0:
        raise ValueError(
            "unidentifiable higher anchor must be filtered before source-state build"
        )

    key = _source_key(item)
    nas_index = indexes["NAS100"].get(key)
    if nas_index is None or nas_index < 60:
        raise ValueError("source state lacks NAS100 frontier history")

    nas = bars["NAS100"]
    prior20 = nas[nas_index - 19 : nas_index + 1]
    prior60 = nas[nas_index - 59 : nas_index + 1]
    if len(prior20) != 20 or len(prior60) != 60:
        raise ValueError("frontier source windows incomplete")

    floor = min(bar.low for bar in prior20)
    peak = max(bar.high for bar in prior20)
    scale = max(1e-9, fmean(bar.high - bar.low for bar in prior20))

    def safe_distance(price: float) -> float:
        return (
            (price - floor) / scale
            if anchor > 0
            else (peak - price) / scale
        )

    now = safe_distance(nas[nas_index].close)
    d5 = safe_distance(nas[nas_index - 5].close)
    d15 = safe_distance(nas[nas_index - 15].close)

    recent5 = nas[nas_index - 4 : nas_index + 1]
    recent15 = nas[nas_index - 14 : nas_index + 1]
    worst5 = min(
        (
            (bar.low - floor) / scale
            if anchor > 0
            else (peak - bar.high) / scale
        )
        for bar in recent5
    )
    worst15 = min(
        (
            (bar.low - floor) / scale
            if anchor > 0
            else (peak - bar.high) / scale
        )
        for bar in recent15
    )

    adverse_closes = 0
    for left, right in zip(recent5, recent5[1:], strict=False):
        move = right.close - left.close
        adverse_closes += int(anchor * move < 0)
    adverse_fraction = adverse_closes / max(1, len(recent5) - 1)

    range5 = fmean(bar.high - bar.low for bar in recent5)
    range20 = fmean(bar.high - bar.low for bar in prior20)
    vol_ratio = range5 / max(1e-9, range20)

    peer_adverse: dict[int, float] = {}
    for horizon in (5, 15):
        values = []
        for market in ("SP500", "US30"):
            peer_index = indexes[market].get(key)
            if peer_index is None or peer_index < horizon:
                raise ValueError("peer source state is incomplete")
            peer = bars[market]
            ret_bps = _return_bps(
                peer[peer_index].close,
                peer[peer_index - horizon].close,
            )
            # Positive means the peer is moving against the higher anchor.
            values.append(max(-5.0, min(5.0, -anchor * ret_bps / 100.0)))
        peer_adverse[horizon] = fmean(values)

    motif = structural_frontier_hierarchy_motif(
        trajectory=item.trajectory,
        anchor_direction=anchor,
    )
    depth = motif.current_depth / 7.0
    recession_minus_advance = max(
        -1.0,
        min(1.0, (motif.recession_count - motif.advance_count) / 4.0),
    )

    return StructuralFrontierSourceState(
        episode_id=item.trajectory.episode_id,
        as_of=snapshot.as_of,
        anchor_direction=anchor,
        distance_now=max(-5.0, min(10.0, now)),
        approach_5m=max(-5.0, min(5.0, d5 - now)),
        approach_15m=max(-5.0, min(5.0, d15 - now)),
        rejection_5m=max(-5.0, min(5.0, now - worst5)),
        rejection_15m=max(-5.0, min(5.0, now - worst15)),
        adverse_close_fraction_5m=adverse_fraction,
        volatility_ratio_5m_20m=max(0.0, min(5.0, vol_ratio)),
        peer_adverse_5m=peer_adverse[5],
        peer_adverse_15m=peer_adverse[15],
        higher_resilience_minus_fragility=max(
            -1.0,
            min(1.0, _higher_resilience_minus_fragility(snapshot)),
        ),
        hierarchy_depth=depth,
        hierarchy_recession_minus_advance=recession_minus_advance,
    )


def _prepare_frontier_partition(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[
    tuple[StructuralFrontierTrainingEpisode, ...],
    dict[str, int | str | None],
]:
    corrected, target_range = relabel_partition_with_structural_failure_v2(
        partition=partition,
        evidence_paths=evidence_paths,
    )
    bars = {market: _load_bars(evidence_paths[market]) for market in MARKETS}
    indexes = {
        market: {bar.closed_key: index for index, bar in enumerate(bars[market])}
        for market in MARKETS
    }

    rows = []
    frontier_unidentifiable_anchor_count = 0
    for item in corrected:
        snapshot = item.trajectory.snapshots[-1]
        if not baseline_local_opposition(snapshot):
            continue
        if higher_timeframe_anchor_direction(snapshot) == 0:
            frontier_unidentifiable_anchor_count += 1
            continue
        source = _build_source_state(item=item, bars=bars, indexes=indexes)
        rows.append(
            StructuralFrontierTrainingEpisode(
                source=source,
                observed_at=item.observed_at,
                terminal_failure=item.terminal_failure,
            )
        )

    return tuple(rows), {
        "episode_count": len(rows),
        "source_min": (
            min(item.source.as_of for item in rows).isoformat()
            if rows
            else None
        ),
        "source_max": (
            max(item.source.as_of for item in rows).isoformat()
            if rows
            else None
        ),
        "target_max": (
            max(item.observed_at for item in rows).isoformat()
            if rows
            else None
        ),
        "v2_terminal_count": sum(item.terminal_failure for item in rows),
        "changed_target_count": target_range["changed_target_count"],
        "target_unidentifiable_anchor_count": target_range[
            "unidentifiable_anchor_count"
        ],
        "frontier_unidentifiable_anchor_count": (
            frontier_unidentifiable_anchor_count
        ),
        "target_contract": TARGET_CONTRACT,
        "fresh_holdout_opened": 0,
    }


def _evaluation_payload(
    evaluation: StructuralFrontierEvaluation,
) -> dict[str, int | str]:
    return {
        "partition": evaluation.partition,
        "sample_count": evaluation.sample_count,
        "baseline_terminal_count": evaluation.baseline_terminal_count,
        "baseline_false_declaration_count": (
            evaluation.baseline_false_declaration_count
        ),
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


def run(*, evidence: dict[str, dict[str, Path]]) -> dict[str, Any]:
    partitions = {}
    ranges = {}
    for partition in PARTITIONS:
        rows, partition_range = _prepare_frontier_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        partitions[partition] = rows
        ranges[partition] = partition_range

    sample_gate = all(
        len(partitions[partition]) >= MINIMUM_EPISODES
        for partition in PARTITIONS
    )
    target_gate = all(
        ranges[partition]["target_contract"] == TARGET_CONTRACT
        and ranges[partition]["fresh_holdout_opened"] == 0
        and int(ranges[partition]["changed_target_count"] or 0) > 0
        for partition in PARTITIONS
    )
    if not sample_gate or not target_gate:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP05_V6_SAMPLE_OR_TARGET_GATE_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "partition_ranges": ranges,
        }

    model = fit_structural_frontier_model(
        fitted_at=max(item.observed_at for item in partitions["r8"]),
        fit_partition="r8",
        episodes=partitions["r8"],
    )
    evaluations = {
        partition: evaluate_structural_frontier(
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
    frozen_model_payload = {
        "fit_partition": model.fit_partition,
        "fit_count": model.fit_count,
        "fit_terminal_count": model.fit_terminal_count,
        "calibration_count": model.calibration_count,
        "calibration_terminal_count": model.calibration_terminal_count,
        "purged_discovery_count": model.purged_discovery_count,
        "discovery_observed_max": model.discovery_observed_max.isoformat(),
        "calibration_source_min": model.calibration_source_min.isoformat(),
        "feature_names": list(model.feature_names),
        "feature_centers_micros": list(model.feature_centers_micros),
        "feature_scales_micros": list(model.feature_scales_micros),
        "coefficients_micros": list(model.coefficients_micros),
        "intercept_micros": model.intercept_micros,
        "declaration_threshold_micros": model.declaration_threshold_micros,
        "calibration_false_reduction_bps": (
            model.calibration_false_reduction_bps
        ),
        "calibration_terminal_preservation_bps": (
            model.calibration_terminal_preservation_bps
        ),
        "representation": "STRUCTURAL_FRONTIER_SURVIVAL_V2_FIXED_ANCHOR",
    }
    frozen_model_fingerprint = hashlib.sha256(
        json.dumps(
            frozen_model_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    protocol_pass = (
        sample_gate
        and target_gate
        and model.fit_partition == "r8"
        and model.calibration_terminal_preservation_bps >= 9_800
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
        "target_contract": TARGET_CONTRACT,
        "status": (
            "WP05_V6_STRUCTURAL_FRONTIER_FROZEN_FOR_FRESH_HOLDOUT"
            if protocol_pass and development_gate_pass
            else "WP05_V6_STRUCTURAL_FRONTIER_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "development_gate_pass": development_gate_pass,
        "fresh_holdout_opened": False,
        "wp05_exit_gate_pass": False,
        "partition_ranges": ranges,
        "model": {
            **frozen_model_payload,
            "feature_count": len(model.feature_names),
            "fingerprint_sha256": frozen_model_fingerprint,
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
            "must_pass_partitions": ["r6", "r5"],
        },
        "governance": {
            "target_v2_required": True,
            "frontier_matches_target_coordinate_system": True,
            "fixed_source_anchor_for_hierarchy_trajectory": True,
            "source_time_frontier_only": True,
            "unidentifiable_higher_anchor_abstains": True,
            "r8_chronological_discovery_calibration_only": True,
            "r6_refit": False,
            "r5_refit": False,
            "r6_threshold_retuning": False,
            "r5_threshold_retuning": False,
            "runtime_future_market_used": False,
            "trade_pnl_used": False,
            "trader_identity_feature_used": False,
            "symbol_identity_feature_used": False,
            "fresh_holdout_opened": False,
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
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_pass": payload["protocol_pass"],
                "development_gate_pass": payload["development_gate_pass"],
                "model": payload.get("model", {}),
                "evaluations": payload.get("evaluations", {}),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
