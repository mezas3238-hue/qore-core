"""WP-05 V7 competing-survival consumed-development experiment.

V7 implements the preregistered dual-mechanism hypothesis without changing the
Target-V2 population or gate. R8 is the only fit/calibration partition. R6/R5
are touched only after a legal R8 calibration candidate exists and are then
used for one-way consumed falsification. Fresh evidence is never opened here.
"""

from __future__ import annotations

import argparse
import gc
import json
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any

from shared_wp03_historical_causal_discovery import MARKETS, _load_bars
from shared_wp05_structural_failure_target_v2 import (
    relabel_partition_with_structural_failure_v2,
)
from shared_wp05_temporal_hierarchy_absorption_v3 import PARTITIONS, _paths
from shared_wp05_temporal_hierarchy_v1 import (
    MINIMUM_BASELINE_TERMINALS,
    MINIMUM_EPISODES,
    MINIMUM_FALSE_REDUCTION_BPS,
    MINIMUM_TERMINAL_PRESERVATION_BPS,
)

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_v7 import (
    CompetingSurvivalEvaluation,
    CompetingSurvivalSourceState,
    CompetingSurvivalTrainingEpisode,
    competing_survival_model_fingerprint,
    evaluate_competing_survival,
    fit_competing_survival_model,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_features_v7 import (
    build_competing_survival_source_state,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    baseline_local_opposition,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_structural_frontier_v6 import (
    structural_frontier_hierarchy_motif,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_target_contract import (
    higher_timeframe_anchor_direction,
)

SCHEMA = "qore.shared.wp05.competing_survival_consumed.v7"
IDENTITY = "QORE_SHARED_WP05_COMPETING_SURVIVAL_HYPOTHESES_V7_001"
REPRESENTATION = "COMPETING_SURVIVAL_HYPOTHESES_V1"
TARGET_CONTRACT = "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2"

_SEQUENCE_MINUTES = 30
_CAUSAL_FRONTIER_BARS = 20
_EPSILON = 1e-9


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _bar_range(bar: Any) -> float:
    return max(_EPSILON, float(bar.high) - float(bar.low))


def _mean_range(rows: tuple[Any, ...]) -> float:
    return max(_EPSILON, fmean(_bar_range(bar) for bar in rows))


def _source_key(item: Any) -> str:
    return item.trajectory.snapshots[-1].as_of.strftime("%Y-%m-%dT%H:%M:%S")


def _level_map(snapshot: TemporalHierarchySnapshot) -> dict[WorldScale, Any]:
    return {level.scale: level for level in snapshot.levels}


def _higher_resilience_minus_fragility(
    snapshot: TemporalHierarchySnapshot,
) -> float:
    levels = _level_map(snapshot)
    rows = [
        levels[scale]
        for scale in (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
        if scale in levels
    ]
    if not rows:
        return 0.0
    return fmean(
        (
            level.persistence_bps
            + level.coherence_bps
            - level.fragility_bps
            - level.transition_bps
        )
        / 20_000.0
        for level in rows
    )


def _higher_transition_pressure(snapshot: TemporalHierarchySnapshot) -> float:
    levels = _level_map(snapshot)
    rows = [
        levels[scale]
        for scale in (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
        if scale in levels
    ]
    if not rows:
        return 0.0
    return fmean(
        (level.fragility_bps + level.transition_bps) / 20_000.0
        for level in rows
    )


def _higher_coherence(snapshot: TemporalHierarchySnapshot) -> float:
    levels = _level_map(snapshot)
    rows = [
        levels[scale]
        for scale in (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
        if scale in levels
    ]
    if not rows:
        return 0.0
    return fmean(level.coherence_bps / 10_000.0 for level in rows)


def _exact_source_distance(
    nas: tuple[Any, ...],
    index: int,
    anchor: int,
) -> tuple[float, float]:
    prior = nas[index - 19 : index + 1]
    if len(prior) != 20:
        raise ValueError("Target-V2 source frontier requires 20 closed bars")
    floor = min(float(bar.low) for bar in prior)
    peak = max(float(bar.high) for bar in prior)
    scale = _mean_range(prior)
    close = float(nas[index].close)
    distance = (
        (close - floor) / scale
        if anchor > 0
        else (peak - close) / scale
    )
    return distance, scale


def _causal_frontier_state(
    nas: tuple[Any, ...],
    index: int,
    anchor: int,
) -> tuple[float, float, bool]:
    """Evaluate one bar against the 20 bars strictly preceding it."""

    prior = nas[index - _CAUSAL_FRONTIER_BARS : index]
    if len(prior) != _CAUSAL_FRONTIER_BARS:
        raise ValueError("causal frontier requires 20 strictly prior bars")
    floor = min(float(bar.low) for bar in prior)
    peak = max(float(bar.high) for bar in prior)
    scale = _mean_range(prior)
    bar = nas[index]
    if anchor > 0:
        distance = (float(bar.close) - floor) / scale
        breach_depth = max(0.0, (floor - float(bar.low)) / scale)
        touch = float(bar.low) <= floor
    else:
        distance = (peak - float(bar.close)) / scale
        breach_depth = max(0.0, (float(bar.high) - peak) / scale)
        touch = float(bar.high) >= peak
    return distance, breach_depth, touch


def _directional_persistence(
    rows: tuple[Any, ...],
    anchor: int,
    *,
    favorable: bool,
) -> float:
    if len(rows) < 2:
        return 0.0
    count = 0
    total = 0
    for left, right in zip(rows, rows[1:], strict=False):
        move = anchor * (float(right.close) - float(left.close))
        total += 1
        count += int(move > 0 if favorable else move < 0)
    return count / max(1, total)


def _consecutive_closes(
    rows: tuple[Any, ...],
    anchor: int,
    *,
    favorable: bool,
) -> float:
    if len(rows) < 2:
        return 0.0
    count = 0
    for left, right in reversed(tuple(zip(rows, rows[1:], strict=False))):
        move = anchor * (float(right.close) - float(left.close))
        matches = move > 0 if favorable else move < 0
        if not matches:
            break
        count += 1
    return float(count)


def _rejection_fraction(rows: tuple[Any, ...], anchor: int) -> float:
    values = []
    for bar in rows:
        width = _bar_range(bar)
        opened = float(bar.opened)
        close = float(bar.close)
        if anchor > 0:
            wick = min(opened, close) - float(bar.low)
        else:
            wick = float(bar.high) - max(opened, close)
        values.append(_clamp(wick / width, 0.0, 1.0))
    return 0.0 if not values else fmean(values)


def _close_location_recovery(bar: Any, anchor: int) -> float:
    width = _bar_range(bar)
    if anchor > 0:
        value = (float(bar.close) - float(bar.low)) / width
    else:
        value = (float(bar.high) - float(bar.close)) / width
    return _clamp(value, 0.0, 1.0)


def _normalized_aligned_move(
    *,
    last: float,
    first: float,
    anchor: int,
    scale: float,
) -> float:
    return anchor * (last - first) / max(_EPSILON, scale)


def _peer_adverse_return(
    peer: tuple[Any, ...],
    index: int,
    horizon: int,
    anchor: int,
) -> float:
    if index < horizon:
        raise ValueError("peer history is incomplete")
    first = float(peer[index - horizon].close)
    last = float(peer[index].close)
    if first == 0.0:
        return 0.0
    aligned_bps = anchor * (last / first - 1.0) * 10_000.0
    return _clamp(-aligned_bps / 100.0, -8.0, 8.0)


def _snapshot_at_offset(item: Any, minutes: int) -> TemporalHierarchySnapshot:
    source = item.trajectory.snapshots[-1].as_of
    best = min(
        item.trajectory.snapshots,
        key=lambda snapshot: abs(
            (source - snapshot.as_of).total_seconds() / 60.0 - minutes
        ),
    )
    gap = abs((source - best.as_of).total_seconds() / 60.0 - minutes)
    if gap > 10.0:
        raise ValueError("hierarchy trajectory lacks required causal offset")
    return best


def _build_source_state(
    *,
    item: Any,
    bars: dict[str, tuple[Any, ...]],
    indexes: dict[str, dict[str, int]],
) -> CompetingSurvivalSourceState:
    """Delegate consumed evidence to the single preregistered causal extractor."""

    snapshot = item.trajectory.snapshots[-1]
    anchor = higher_timeframe_anchor_direction(snapshot)
    if anchor == 0:
        raise ValueError("unidentifiable anchor must be filtered before V7 build")

    key = _source_key(item)
    nas_index = indexes["NAS100"].get(key)
    sp500_index = indexes["SP500"].get(key)
    us30_index = indexes["US30"].get(key)
    if nas_index is None or sp500_index is None or us30_index is None:
        raise ValueError("V7 source state is missing aligned market evidence")

    source = build_competing_survival_source_state(
        trajectory=item.trajectory,
        anchor_direction=anchor,
        nas_bars=bars["NAS100"],
        nas_index=nas_index,
        sp500_bars=bars["SP500"],
        sp500_index=sp500_index,
        us30_bars=bars["US30"],
        us30_index=us30_index,
    )
    if not source.evidence_complete:
        raise ValueError("V7 canonical extractor reports incomplete causal evidence")
    return source

def _prepare_partition(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[
    tuple[CompetingSurvivalTrainingEpisode, ...],
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

    rows: list[CompetingSurvivalTrainingEpisode] = []
    unidentifiable = 0
    incomplete = 0
    for item in corrected:
        snapshot = item.trajectory.snapshots[-1]
        if not baseline_local_opposition(snapshot):
            continue
        if higher_timeframe_anchor_direction(snapshot) == 0:
            unidentifiable += 1
            continue
        try:
            source = _build_source_state(
                item=item,
                bars=bars,
                indexes=indexes,
            )
        except ValueError:
            incomplete += 1
            continue
        rows.append(
            CompetingSurvivalTrainingEpisode(
                source=source,
                observed_at=item.observed_at,
                terminal_failure=item.terminal_failure,
            )
        )

    result = tuple(rows)
    del corrected
    del bars
    del indexes
    gc.collect()
    return result, {
        "episode_count": len(result),
        "source_min": (
            min(item.source.as_of for item in result).isoformat()
            if result
            else None
        ),
        "source_max": (
            max(item.source.as_of for item in result).isoformat()
            if result
            else None
        ),
        "target_max": (
            max(item.observed_at for item in result).isoformat()
            if result
            else None
        ),
        "terminal_count": sum(item.terminal_failure for item in result),
        "target_unidentifiable_anchor_count": target_range[
            "unidentifiable_anchor_count"
        ],
        "v7_unidentifiable_anchor_count": unidentifiable,
        "incomplete_source_count": incomplete,
        "changed_target_count": target_range["changed_target_count"],
        "target_contract": TARGET_CONTRACT,
        "fresh_holdout_opened": 0,
    }


def _temporal_order_pass(
    ranges: dict[str, dict[str, int | str | None]],
) -> bool:
    for left_partition, right_partition in (("r8", "r6"), ("r6", "r5")):
        left = ranges[left_partition]["target_max"]
        right = ranges[right_partition]["source_min"]
        if not isinstance(left, str) or not isinstance(right, str):
            return False
        if datetime.fromisoformat(left) >= datetime.fromisoformat(right):
            return False
    return True


def _evaluation_payload(
    evaluation: CompetingSurvivalEvaluation,
) -> dict[str, int | str]:
    return {
        "partition": evaluation.partition,
        "sample_count": evaluation.sample_count,
        "baseline_terminal_count": evaluation.baseline_terminal_count,
        "baseline_false_declaration_count": (
            evaluation.baseline_false_declaration_count
        ),
        "competing_false_declaration_count": (
            evaluation.competing_false_declaration_count
        ),
        "competing_missed_terminal_count": (
            evaluation.competing_missed_terminal_count
        ),
        "recovery_supported_count": evaluation.recovery_supported_count,
        "unresolved_count": evaluation.unresolved_count,
        "terminal_supported_count": evaluation.terminal_supported_count,
        "false_declaration_reduction_bps": (
            evaluation.false_declaration_reduction_bps
        ),
        "terminal_detection_preservation_bps": (
            evaluation.terminal_detection_preservation_bps
        ),
    }


def _model_payload(model: Any) -> dict[str, Any]:
    return {
        "fit_partition": model.fit_partition,
        "representation": REPRESENTATION,
        "fit_count": model.fit_count,
        "fit_terminal_count": model.fit_terminal_count,
        "calibration_count": model.calibration_count,
        "calibration_terminal_count": model.calibration_terminal_count,
        "purged_discovery_count": model.purged_discovery_count,
        "discovery_observed_max": model.discovery_observed_max.isoformat(),
        "calibration_source_min": model.calibration_source_min.isoformat(),
        "terminal_feature_names": list(model.terminal_feature_names),
        "recovery_feature_names": list(model.recovery_feature_names),
        "terminal_centers_micros": list(model.terminal_centers_micros),
        "terminal_scales_micros": list(model.terminal_scales_micros),
        "terminal_coefficients_micros": list(model.terminal_coefficients_micros),
        "terminal_intercept_micros": model.terminal_intercept_micros,
        "recovery_centers_micros": list(model.recovery_centers_micros),
        "recovery_scales_micros": list(model.recovery_scales_micros),
        "recovery_coefficients_micros": list(model.recovery_coefficients_micros),
        "recovery_intercept_micros": model.recovery_intercept_micros,
        "terminal_threshold_micros": model.terminal_threshold_micros,
        "recovery_threshold_micros": model.recovery_threshold_micros,
        "calibration_terminal_preservation_bps": (
            model.calibration_terminal_preservation_bps
        ),
        "calibration_false_reduction_bps": model.calibration_false_reduction_bps,
        "calibration_gate_pass": model.calibration_gate_pass,
        "fingerprint_sha256": competing_survival_model_fingerprint(model),
    }


def run(*, evidence: dict[str, dict[str, Path]]) -> dict[str, Any]:
    r8_rows, r8_range = _prepare_partition(
        partition="r8",
        evidence_paths=evidence["r8"],
    )
    ranges: dict[str, dict[str, int | str | None]] = {"r8": r8_range}
    if len(r8_rows) < MINIMUM_EPISODES:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP05_V7_PROTOCOL_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "partition_ranges": ranges,
            "reason": "R8_SAMPLE_GATE_FAILED",
        }

    model = fit_competing_survival_model(
        fitted_at=max(item.observed_at for item in r8_rows),
        fit_partition="r8",
        episodes=r8_rows,
    )
    r8_evaluation = evaluate_competing_survival(
        model=model,
        partition="r8",
        episodes=r8_rows,
    )

    if not model.calibration_gate_pass:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "status": "WP05_V7_COMPETING_SURVIVAL_FALSIFIED",
            "protocol_pass": True,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "wp05_exit_gate_pass": False,
            "partition_ranges": ranges,
            "model": _model_payload(model),
            "evaluations": {"r8": _evaluation_payload(r8_evaluation)},
            "reason": "NO_LEGAL_R8_CALIBRATION_THRESHOLD_PAIR",
            "governance": _governance_payload(),
        }

    partitions: dict[str, tuple[CompetingSurvivalTrainingEpisode, ...]] = {
        "r8": r8_rows
    }
    for partition in ("r6", "r5"):
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
    target_gate = all(
        ranges[partition]["target_contract"] == TARGET_CONTRACT
        and int(ranges[partition]["changed_target_count"] or 0) > 0
        and ranges[partition]["fresh_holdout_opened"] == 0
        for partition in PARTITIONS
    )
    temporal_gate = _temporal_order_pass(ranges)
    if not sample_gate or not target_gate or not temporal_gate:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "status": "WP05_V7_PROTOCOL_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "partition_ranges": ranges,
            "model": _model_payload(model),
            "reason": "SAMPLE_TARGET_OR_TEMPORAL_GATE_FAILED",
            "governance": _governance_payload(),
        }

    evaluations = {
        partition: evaluate_competing_survival(
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
        and target_gate
        and temporal_gate
        and model.calibration_gate_pass
        and model.fit_partition == "r8"
        and model.target_used_for_training_only is True
        and model.runtime_future_market_used is False
        and model.outcome_used_at_runtime is False
        and model.trader_identity_used is False
        and model.symbol_identity_used is False
        and model.setup_identity_used is False
        and model.pnl_used_at_runtime is False
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
        "representation": REPRESENTATION,
        "status": (
            "WP05_V7_FROZEN_FOR_FRESH_HOLDOUT"
            if protocol_pass and development_gate_pass
            else "WP05_V7_COMPETING_SURVIVAL_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "development_gate_pass": development_gate_pass,
        "fresh_holdout_opened": False,
        "wp05_exit_gate_pass": False,
        "partition_temporal_order_gate": temporal_gate,
        "partition_ranges": ranges,
        "model": _model_payload(model),
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
        "governance": _governance_payload(),
    }


def _governance_payload() -> dict[str, bool]:
    return {
        "target_v2_required": True,
        "dual_mechanism_heads_required": True,
        "unresolved_preserves_baseline": True,
        "fixed_source_anchor_for_hierarchy_trajectory": True,
        "causal_historical_frontier_excludes_evaluated_bar": True,
        "r8_chronological_discovery_calibration_only": True,
        "r6_refit": False,
        "r5_refit": False,
        "r6_threshold_retuning": False,
        "r5_threshold_retuning": False,
        "runtime_future_market_used": False,
        "trade_pnl_used": False,
        "trader_identity_feature_used": False,
        "symbol_identity_feature_used": False,
        "setup_identity_feature_used": False,
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
