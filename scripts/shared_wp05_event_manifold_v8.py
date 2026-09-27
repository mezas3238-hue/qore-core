"""WP-05 V8 censored event-manifold consumed-development experiment.

V8 keeps the V7 causal source representation but replaces the complement-label
dual-head ontology with explicit TERMINAL_EVENT, VERIFIED_RECOVERY_EVENT and
CENSORED_UNKNOWN historical states. R8 is fitted/calibrated before R6/R5 may be
read. Fresh holdout remains closed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
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

from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_features_v7 import (
    build_competing_survival_source_state,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    baseline_local_opposition,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_event_manifold_v8 import (
    EventManifoldEvaluation,
    EventManifoldLabel,
    EventManifoldTrainingEpisode,
    event_manifold_model_fingerprint,
    event_manifold_representation_fingerprint,
    evaluate_event_manifold,
    fit_event_manifold_model,
    matured_event_label,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_target_contract import (
    higher_timeframe_anchor_direction,
)

SCHEMA = "qore.shared.wp05.event_manifold_consumed.v8"
IDENTITY = "QORE_SHARED_WP05_EVENT_MANIFOLD_WITH_CENSORING_V8_001"
TARGET_CONTRACT = "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2"
REPRESENTATION = "ROBUST_TERMINAL_RECOVERY_EVENT_MANIFOLDS_WITH_CENSORING_V8_001"


def _source_key(item: Any) -> str:
    return item.trajectory.snapshots[-1].as_of.strftime("%Y-%m-%dT%H:%M:%S")


def _prepare_partition(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[
    tuple[EventManifoldTrainingEpisode, ...],
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

    rows: list[EventManifoldTrainingEpisode] = []
    unidentifiable_anchor_count = 0
    incomplete_evidence_count = 0
    terminal_count = 0
    recovery_count = 0
    censored_count = 0

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
        missing_index = False
        for market in MARKETS:
            market_index = indexes[market].get(key)
            if market_index is None:
                missing_index = True
                break
            source_indexes[market] = market_index
        if missing_index:
            incomplete_evidence_count += 1
            continue

        nas_index = source_indexes["NAS100"]
        if nas_index < 19 or nas_index + 30 >= len(bars["NAS100"]):
            incomplete_evidence_count += 1
            continue

        prior = bars["NAS100"][nas_index - 19 : nas_index + 1]
        future = bars["NAS100"][nas_index + 1 : nas_index + 31]
        if len(prior) != 20 or len(future) != 30:
            incomplete_evidence_count += 1
            continue

        label = matured_event_label(
            anchor_direction=anchor,
            prior_peak=max(bar.high for bar in prior),
            prior_floor=min(bar.low for bar in prior),
            future_bars=future,
        )
        if (
            label is EventManifoldLabel.TERMINAL_EVENT
        ) != bool(item.terminal_failure):
            raise AssertionError("V8 terminal event diverges from Target V2")

        source = build_competing_survival_source_state(
            trajectory=item.trajectory,
            anchor_direction=anchor,
            nas_bars=bars["NAS100"],
            nas_index=nas_index,
            sp500_bars=bars["SP500"],
            sp500_index=source_indexes["SP500"],
            us30_bars=bars["US30"],
            us30_index=source_indexes["US30"],
        )
        incomplete_evidence_count += int(not source.evidence_complete)
        terminal_count += int(label is EventManifoldLabel.TERMINAL_EVENT)
        recovery_count += int(
            label is EventManifoldLabel.VERIFIED_RECOVERY_EVENT
        )
        censored_count += int(label is EventManifoldLabel.CENSORED_UNKNOWN)
        rows.append(
            EventManifoldTrainingEpisode(
                source=source,
                observed_at=item.observed_at,
                label=label,
            )
        )

    return tuple(rows), {
        "episode_count": len(rows),
        "complete_evidence_count": sum(
            item.source.evidence_complete for item in rows
        ),
        "incomplete_evidence_count": incomplete_evidence_count,
        "terminal_event_count": terminal_count,
        "verified_recovery_event_count": recovery_count,
        "censored_unknown_count": censored_count,
        "source_min": (
            min(item.source.as_of for item in rows).isoformat() if rows else None
        ),
        "source_max": (
            max(item.source.as_of for item in rows).isoformat() if rows else None
        ),
        "target_max": (
            max(item.observed_at for item in rows).isoformat() if rows else None
        ),
        "changed_target_count": target_range["changed_target_count"],
        "target_unidentifiable_anchor_count": target_range[
            "unidentifiable_anchor_count"
        ],
        "v8_unidentifiable_anchor_count": unidentifiable_anchor_count,
        "target_contract": TARGET_CONTRACT,
        "fresh_holdout_opened": 0,
    }


def _partition_temporal_order_pass(
    ranges: dict[str, dict[str, int | str | None]],
) -> bool:
    required = (
        ("r8", "target_max", "r6", "source_min"),
        ("r6", "target_max", "r5", "source_min"),
    )
    for left_partition, left_key, right_partition, right_key in required:
        left = ranges[left_partition][left_key]
        right = ranges[right_partition][right_key]
        if not isinstance(left, str) or not isinstance(right, str):
            return False
        if datetime.fromisoformat(left) >= datetime.fromisoformat(right):
            return False
    return True


def _evaluation_payload(
    evaluation: EventManifoldEvaluation,
) -> dict[str, int | str]:
    return asdict(evaluation)


def _governance_payload() -> dict[str, bool | str]:
    return {
        "preregistered_identity": IDENTITY,
        "target_v2_required": True,
        "v7_source_representation_frozen": True,
        "terminal_event_is_exact_target_v2": True,
        "recovery_is_not_terminal_complement": True,
        "censored_unknown_defines_no_manifold": True,
        "recovery_persistence_closes": "3",
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
        "feature_centers_micros": list(model.feature_centers_micros),
        "feature_scales_micros": list(model.feature_scales_micros),
        "terminal_centers_micros": list(model.terminal_centers_micros),
        "terminal_scales_micros": list(model.terminal_scales_micros),
        "recovery_centers_micros": list(model.recovery_centers_micros),
        "recovery_scales_micros": list(model.recovery_scales_micros),
        "recovery_radius_micros": model.recovery_radius_micros,
        "recovery_radius_quantile_bps": model.recovery_radius_quantile_bps,
        "recovery_advantage_margin_micros": (
            model.recovery_advantage_margin_micros
        ),
        "calibration_terminal_preservation_bps": (
            model.calibration_terminal_preservation_bps
        ),
        "calibration_false_reduction_bps": (
            model.calibration_false_reduction_bps
        ),
        "calibration_gate_pass": model.calibration_gate_pass,
        "fit_count": model.fit_count,
        "fit_terminal_count": model.fit_terminal_count,
        "fit_recovery_count": model.fit_recovery_count,
        "fit_censored_count": model.fit_censored_count,
        "calibration_count": model.calibration_count,
        "calibration_terminal_count": model.calibration_terminal_count,
        "calibration_recovery_count": model.calibration_recovery_count,
        "calibration_censored_count": model.calibration_censored_count,
        "purged_discovery_count": model.purged_discovery_count,
        "discovery_observed_max": model.discovery_observed_max.isoformat(),
        "calibration_source_min": model.calibration_source_min.isoformat(),
        "fingerprint_sha256": event_manifold_model_fingerprint(model),
        "representation_fingerprint_sha256": (
            event_manifold_representation_fingerprint()
        ),
        "representation": REPRESENTATION,
    }


def run(*, evidence: dict[str, dict[str, Path]]) -> dict[str, Any]:
    # R8 must be fully prepared/fitted/calibrated before R6/R5 are opened.
    r8_rows, r8_range = _prepare_partition(
        partition="r8",
        evidence_paths=evidence["r8"],
    )
    ranges: dict[str, dict[str, int | str | None]] = {"r8": r8_range}
    r8_complete = tuple(
        item for item in r8_rows if item.source.evidence_complete
    )
    r8_target_gate = (
        r8_range["target_contract"] == TARGET_CONTRACT
        and r8_range["fresh_holdout_opened"] == 0
        and int(r8_range["changed_target_count"] or 0) > 0
    )
    r8_event_gate = (
        int(r8_range["terminal_event_count"] or 0) >= MINIMUM_BASELINE_TERMINALS
        and int(r8_range["verified_recovery_event_count"] or 0) >= 100
    )
    if (
        len(r8_rows) < MINIMUM_EPISODES
        or len(r8_complete) < MINIMUM_EPISODES
        or not r8_target_gate
        or not r8_event_gate
    ):
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "representation": REPRESENTATION,
            "status": "WP05_V8_PROTOCOL_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "wp05_exit_gate_pass": False,
            "partition_ranges": ranges,
            "reason": "R8_SAMPLE_TARGET_OR_EVENT_GATE_FAILED",
            "governance": _governance_payload(),
        }

    model = fit_event_manifold_model(
        fitted_at=max(item.observed_at for item in r8_complete),
        fit_partition="r8",
        episodes=r8_complete,
    )
    model_payload = _model_payload(model)
    r8_evaluation = evaluate_event_manifold(
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
            "status": "WP05_V8_EVENT_MANIFOLD_FALSIFIED",
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
            "reason": "NO_LEGAL_R8_CALIBRATION_REGION",
            "governance": _governance_payload(),
        }

    partitions: dict[str, tuple[EventManifoldTrainingEpisode, ...]] = {
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
    complete_evidence_gate = all(
        int(ranges[partition]["complete_evidence_count"] or 0)
        >= MINIMUM_EPISODES
        for partition in PARTITIONS
    )
    target_gate = all(
        ranges[partition]["target_contract"] == TARGET_CONTRACT
        and ranges[partition]["fresh_holdout_opened"] == 0
        and int(ranges[partition]["changed_target_count"] or 0) > 0
        for partition in PARTITIONS
    )
    partition_temporal_order_gate = _partition_temporal_order_pass(ranges)

    if (
        not sample_gate
        or not complete_evidence_gate
        or not target_gate
        or not partition_temporal_order_gate
    ):
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "target_contract": TARGET_CONTRACT,
            "representation": REPRESENTATION,
            "status": "WP05_V8_PROTOCOL_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "wp05_exit_gate_pass": False,
            "partition_temporal_order_gate": partition_temporal_order_gate,
            "partition_ranges": ranges,
            "model": model_payload,
            "reason": "SAMPLE_EVIDENCE_TARGET_OR_TEMPORAL_GATE_FAILED",
            "governance": _governance_payload(),
        }

    evaluations = {
        partition: evaluate_event_manifold(
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
        and complete_evidence_gate
        and target_gate
        and partition_temporal_order_gate
        and model.fit_partition == "r8"
        and model.calibration_gate_pass is True
        and model.calibration_terminal_preservation_bps >= 9_800
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
    )
    fingerprint = model_payload["fingerprint_sha256"]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "target_contract": TARGET_CONTRACT,
        "representation": REPRESENTATION,
        "status": (
            "WP05_V8_EVENT_MANIFOLD_FROZEN_FOR_FRESH_HOLDOUT"
            if protocol_pass and development_gate_pass
            else "WP05_V8_EVENT_MANIFOLD_FALSIFIED"
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
