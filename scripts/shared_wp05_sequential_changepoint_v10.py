"""WP-05 V10 causal sequential change-point consumed-development experiment.

V9 is an online early-warning experiment. It compares source-only cognition with
causal evidence accumulated at 0/3/5/10/15 minutes after source. The matured
30-minute Target-V2 label is offline-only. R8 is fitted/calibrated before R6/R5
may be scientifically opened. Fresh holdout remains closed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import MARKETS, _load_bars, _parse_key
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

from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_features_v7 import (
    build_competing_survival_source_state,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    baseline_local_opposition,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_sequential_changepoint_v10 import (
    V10_CHECKPOINTS_MINUTES,
    SequentialChangePointEvaluation,
    SequentialChangePointTrainingEpisode,
    build_sequential_checkpoint_evidence,
    evaluate_sequential_changepoint,
    fit_sequential_changepoint_model,
    sequential_changepoint_model_fingerprint,
    sequential_changepoint_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_target_contract import (
    higher_timeframe_anchor_direction,
)

SCHEMA = "qore.shared.wp05.sequential_changepoint_consumed.v10"
IDENTITY = "QORE_SHARED_WP05_CAUSAL_SEQUENTIAL_CHANGEPOINT_V10_001"
TARGET_CONTRACT = "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2"
REPRESENTATION = "CAUSAL_SEQUENTIAL_LLR_EARLY_WARNING_V10_001"


def _source_key(item: Any) -> str:
    return item.trajectory.snapshots[-1].as_of.strftime("%Y-%m-%dT%H:%M:%S")


def _prepare_partition(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[
    tuple[SequentialChangePointTrainingEpisode, ...],
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

    rows: list[SequentialChangePointTrainingEpisode] = []
    unidentifiable_anchor_count = 0
    incomplete_evidence_count = 0
    terminal_count = 0

    for item in corrected:
        snapshot = item.trajectory.snapshots[-1]
        if not baseline_local_opposition(snapshot):
            continue

        anchor = higher_timeframe_anchor_direction(snapshot)
        if anchor == 0:
            unidentifiable_anchor_count += 1
            continue

        key = _source_key(item)
        source_indexes: dict[str, int] = {}
        missing = False
        for market in MARKETS:
            market_index = indexes[market].get(key)
            if market_index is None:
                missing = True
                break
            source_indexes[market] = market_index
        if missing:
            incomplete_evidence_count += 1
            continue

        if any(
            source_indexes[market] + max(V10_CHECKPOINTS_MINUTES)
            >= len(bars[market])
            for market in MARKETS
        ):
            incomplete_evidence_count += 1
            continue

        source = build_competing_survival_source_state(
            trajectory=item.trajectory,
            anchor_direction=anchor,
            nas_bars=bars["NAS100"],
            nas_index=source_indexes["NAS100"],
            sp500_bars=bars["SP500"],
            sp500_index=source_indexes["SP500"],
            us30_bars=bars["US30"],
            us30_index=source_indexes["US30"],
        )
        if not source.evidence_complete:
            incomplete_evidence_count += 1
            continue

        checkpoints = []
        aligned = True
        source_at = item.trajectory.snapshots[-1].as_of
        for minute in V10_CHECKPOINTS_MINUTES:
            nas_bar = bars["NAS100"][source_indexes["NAS100"] + minute]
            checkpoint_key = nas_bar.closed_key
            checkpoint_at = _parse_key(checkpoint_key)
            elapsed_minutes = (checkpoint_at - source_at).total_seconds() / 60.0
            if abs(elapsed_minutes - minute) > 1.5:
                aligned = False
                break
            if any(
                bars[market][source_indexes[market] + minute].closed_key
                != checkpoint_key
                for market in MARKETS
            ):
                aligned = False
                break
            checkpoints.append(
                build_sequential_checkpoint_evidence(
                    source=source,
                    checkpoint_minutes=minute,
                    as_of=checkpoint_at,
                    nas_bars=bars["NAS100"],
                    nas_source_index=source_indexes["NAS100"],
                    sp500_bars=bars["SP500"],
                    sp500_source_index=source_indexes["SP500"],
                    us30_bars=bars["US30"],
                    us30_source_index=source_indexes["US30"],
                )
            )
        if not aligned:
            incomplete_evidence_count += 1
            continue

        row = SequentialChangePointTrainingEpisode(
            checkpoints=tuple(checkpoints),
            observed_at=item.observed_at,
            terminal_failure=bool(item.terminal_failure),
        )
        rows.append(row)
        terminal_count += int(item.terminal_failure)

    return tuple(rows), {
        "episode_count": len(rows),
        "complete_evidence_count": len(rows),
        "incomplete_evidence_count": incomplete_evidence_count,
        "terminal_event_count": terminal_count,
        "nonterminal_event_count": len(rows) - terminal_count,
        "source_min": (
            min(item.checkpoints[0].as_of for item in rows).isoformat()
            if rows
            else None
        ),
        "source_max": (
            max(item.checkpoints[0].as_of for item in rows).isoformat()
            if rows
            else None
        ),
        "target_max": (
            max(item.observed_at for item in rows).isoformat() if rows else None
        ),
        "changed_target_count": target_range["changed_target_count"],
        "target_unidentifiable_anchor_count": target_range[
            "unidentifiable_anchor_count"
        ],
        "v9_unidentifiable_anchor_count": unidentifiable_anchor_count,
        "target_contract": TARGET_CONTRACT,
        "fresh_holdout_opened": 0,
    }


def _partition_temporal_order_pass(
    ranges: dict[str, dict[str, int | str | None]],
) -> bool:
    for left, right in (("r8", "r6"), ("r6", "r5")):
        left_target = ranges[left]["target_max"]
        right_source = ranges[right]["source_min"]
        if not isinstance(left_target, str) or not isinstance(right_source, str):
            return False
        if _parse_key(left_target[:19]) >= _parse_key(right_source[:19]):
            return False
    return True


def _evaluation_payload(
    evaluation: SequentialChangePointEvaluation,
) -> dict[str, int | str]:
    return asdict(evaluation)


def _governance_payload() -> dict[str, bool | str | list[int]]:
    return {
        "preregistered_identity": IDENTITY,
        "target_v2_required": True,
        "checkpoints_minutes": list(V10_CHECKPOINTS_MINUTES),
        "max_decision_latency_minutes": 15,
        "unresolved_is_abstention": True,
        "terminal_detection_absorbing": True,
        "source_only_diagnostic_required": True,
        "r8_chronological_discovery_calibration_only": True,
        "r6_r5_unread_until_r8_model_frozen": True,
        "r8_r6_r5_temporally_ordered_nonoverlap_required": True,
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


def _model_payload(model: Any) -> dict[str, Any]:
    return {
        "fit_partition": model.fit_partition,
        "feature_names": list(model.feature_names),
        "feature_count": len(model.feature_names),
        "checkpoints_minutes": list(model.checkpoints_minutes),
        "source_only_threshold_micros": model.source_only_threshold_micros,
        "sequential_threshold_micros": model.sequential_threshold_micros,
        "calibration_source_terminal_preservation_bps": (
            model.calibration_source_terminal_preservation_bps
        ),
        "calibration_source_false_reduction_bps": (
            model.calibration_source_false_reduction_bps
        ),
        "calibration_sequential_terminal_preservation_bps": (
            model.calibration_sequential_terminal_preservation_bps
        ),
        "calibration_sequential_false_reduction_bps": (
            model.calibration_sequential_false_reduction_bps
        ),
        "calibration_gate_pass": model.calibration_gate_pass,
        "fit_count": model.fit_count,
        "fit_terminal_count": model.fit_terminal_count,
        "fit_nonterminal_count": model.fit_nonterminal_count,
        "calibration_count": model.calibration_count,
        "calibration_terminal_count": model.calibration_terminal_count,
        "calibration_nonterminal_count": model.calibration_nonterminal_count,
        "purged_discovery_count": model.purged_discovery_count,
        "discovery_observed_max": model.discovery_observed_max.isoformat(),
        "calibration_source_min": model.calibration_source_min.isoformat(),
        "densities": [asdict(item) for item in model.densities],
        "fingerprint_sha256": sequential_changepoint_model_fingerprint(model),
        "representation_fingerprint_sha256": (
            sequential_changepoint_representation_fingerprint()
        ),
        "representation": REPRESENTATION,
    }


def run(*, evidence: dict[str, dict[str, Path]]) -> dict[str, Any]:
    r8_rows, r8_range = _prepare_partition(
        partition="r8",
        evidence_paths=evidence["r8"],
    )
    ranges: dict[str, dict[str, int | str | None]] = {"r8": r8_range}
    r8_gate = (
        len(r8_rows) >= MINIMUM_EPISODES
        and int(r8_range["complete_evidence_count"] or 0) >= MINIMUM_EPISODES
        and int(r8_range["terminal_event_count"] or 0)
        >= MINIMUM_BASELINE_TERMINALS
        and r8_range["target_contract"] == TARGET_CONTRACT
        and r8_range["fresh_holdout_opened"] == 0
        and int(r8_range["changed_target_count"] or 0) > 0
    )
    if not r8_gate:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "representation": REPRESENTATION,
            "status": "WP05_V10_PROTOCOL_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "wp05_exit_gate_pass": False,
            "partition_ranges": ranges,
            "reason": "R8_SAMPLE_TARGET_GATE_FAILED",
            "governance": _governance_payload(),
        }

    model = fit_sequential_changepoint_model(
        fitted_at=max(item.observed_at for item in r8_rows),
        fit_partition="r8",
        episodes=r8_rows,
    )
    model_payload = _model_payload(model)
    r8_evaluation = evaluate_sequential_changepoint(
        model=model,
        partition="r8",
        episodes=r8_rows,
    )
    if not model.calibration_gate_pass:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "representation": REPRESENTATION,
            "status": "WP05_V10_CAUSAL_SEQUENTIAL_FALSIFIED",
            "protocol_pass": True,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "wp05_exit_gate_pass": False,
            "partition_ranges": ranges,
            "model": model_payload,
            "partition_model_fingerprints": {
                "r8": model_payload["fingerprint_sha256"]
            },
            "evaluations": {"r8": _evaluation_payload(r8_evaluation)},
            "reason": "NO_LEGAL_R8_SEQUENTIAL_CALIBRATION",
            "governance": _governance_payload(),
        }

    partitions: dict[str, tuple[SequentialChangePointTrainingEpisode, ...]] = {
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
    terminal_gate = all(
        int(ranges[partition]["terminal_event_count"] or 0)
        >= MINIMUM_BASELINE_TERMINALS
        for partition in PARTITIONS
    )
    target_gate = all(
        ranges[partition]["target_contract"] == TARGET_CONTRACT
        and ranges[partition]["fresh_holdout_opened"] == 0
        and int(ranges[partition]["changed_target_count"] or 0) > 0
        for partition in PARTITIONS
    )
    partition_temporal_order_gate = _partition_temporal_order_pass(ranges)

    if not (
        sample_gate
        and terminal_gate
        and target_gate
        and partition_temporal_order_gate
    ):
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "representation": REPRESENTATION,
            "status": "WP05_V10_PROTOCOL_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "wp05_exit_gate_pass": False,
            "partition_temporal_order_gate": partition_temporal_order_gate,
            "partition_ranges": ranges,
            "model": model_payload,
            "reason": "SAMPLE_TARGET_OR_TEMPORAL_GATE_FAILED",
            "governance": _governance_payload(),
        }

    evaluations = {
        partition: evaluate_sequential_changepoint(
            model=model,
            partition=partition,
            episodes=partitions[partition],
        )
        for partition in PARTITIONS
    }
    development_gate_pass = all(
        evaluations[partition].sequential_false_declaration_reduction_bps
        >= MINIMUM_FALSE_REDUCTION_BPS
        and evaluations[partition].sequential_terminal_detection_preservation_bps
        >= MINIMUM_TERMINAL_PRESERVATION_BPS
        for partition in ("r6", "r5")
    )

    protocol_pass = (
        model.fit_partition == "r8"
        and model.calibration_gate_pass is True
        and model.calibration_sequential_terminal_preservation_bps >= 9_800
        and model.discovery_observed_max < model.calibration_source_min
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
        and partition_temporal_order_gate
    )
    fingerprint = model_payload["fingerprint_sha256"]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "target_contract": TARGET_CONTRACT,
        "representation": REPRESENTATION,
        "status": (
            "WP05_V10_CAUSAL_SEQUENTIAL_FROZEN_FOR_FRESH_HOLDOUT"
            if protocol_pass and development_gate_pass
            else "WP05_V10_CAUSAL_SEQUENTIAL_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "development_gate_pass": development_gate_pass,
        "fresh_holdout_opened": False,
        "wp05_exit_gate_pass": False,
        "partition_temporal_order_gate": partition_temporal_order_gate,
        "partition_ranges": ranges,
        "model": model_payload,
        "partition_model_fingerprints": {
            partition: fingerprint for partition in PARTITIONS
        },
        "evaluations": {
            partition: _evaluation_payload(evaluation)
            for partition, evaluation in evaluations.items()
        },
        "observability_diagnostic": {
            partition: {
                "source_only_false_reduction_bps": (
                    evaluations[partition].source_only_false_declaration_reduction_bps
                ),
                "sequential_false_reduction_bps": (
                    evaluations[partition].sequential_false_declaration_reduction_bps
                ),
                "incremental_false_reduction_bps": (
                    evaluations[partition].sequential_false_declaration_reduction_bps
                    - evaluations[
                        partition
                    ].source_only_false_declaration_reduction_bps
                ),
            }
            for partition in PARTITIONS
        },
        "frozen_development_gate": {
            "minimum_false_declaration_reduction_bps": (
                MINIMUM_FALSE_REDUCTION_BPS
            ),
            "minimum_terminal_detection_preservation_bps": (
                MINIMUM_TERMINAL_PRESERVATION_BPS
            ),
            "must_pass_partitions": ["r6", "r5"],
            "maximum_detection_latency_minutes": 15,
        },
        "governance": _governance_payload(),
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
                "observability_diagnostic": payload.get(
                    "observability_diagnostic",
                    {},
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
