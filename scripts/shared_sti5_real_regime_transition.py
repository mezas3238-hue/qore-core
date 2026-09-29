#!/usr/bin/env python3
"""STI-5 real historical regime-transition replay on immutable market evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Any

from shared_sti2_real_opportunity_discovery import (
    PARTITIONS,
    _aligned_source_rows,
    _paths,
)
from shared_wp03_historical_causal_discovery import _parse_key, _target_state

from qore.infrastructure.core_stack_v2.dynamic_causal_graph import CausalConcept
from qore.infrastructure.core_stack_v2.shared_regime_transition_intelligence import (
    assess_shared_regime_transition,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedRegimeTransitionState,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    DynamicTransitionPolicy,
    MarketTransitionObservation,
    assess_market_trajectory,
)

IDENTITY = "QORE_SHARED_STI5_REAL_REGIME_TRANSITION_V1"
SCHEMA = "qore.shared.sti5.real_regime_transition.v1"
FUTURE_TRANSITION_TARGET_BPS = 6_500
MIN_PRECISION_BPS = 5_500
MIN_RECALL_BPS = 4_000
MAX_FALSE_ALERT_RATE_BPS = 4_500
MAX_MISSED_TRANSITION_RATE_BPS = 6_000
SEQUENCE_WINDOW = 4


def _mean(*values: int) -> int:
    return sum(values) // len(values)


def _transition_observation(
    source: Any,
    states: dict[CausalConcept, int],
) -> MarketTransitionObservation:
    return MarketTransitionObservation(
        as_of=source.as_of,
        data_integrity_bps=source.data_integrity_bps,
        trend_support_bps=_mean(
            states[CausalConcept.DISPLACEMENT],
            states[CausalConcept.ACCEPTANCE],
            states[CausalConcept.MOMENTUM_PERSISTENCE],
        ),
        momentum_bps=states[CausalConcept.MOMENTUM_PERSISTENCE],
        displacement_bps=states[CausalConcept.DISPLACEMENT],
        liquidity_capacity_bps=10_000 - states[CausalConcept.LIQUIDITY_VACUUM],
        volatility_stability_bps=(
            10_000 - states[CausalConcept.REGIME_TRANSITION]
        ),
        cross_market_confirmation_bps=states[
            CausalConcept.LEADER_CONFIRMATION
        ],
        correlation_stability_bps=(
            10_000 - states[CausalConcept.LEADER_DIVERGENCE]
        ),
        contradiction_bps=_mean(
            states[CausalConcept.FAILED_AUCTION],
            states[CausalConcept.ABSORPTION],
            states[CausalConcept.LEADER_DIVERGENCE],
            states[CausalConcept.MOMENTUM_DECAY],
        ),
        anomaly_bps=states[CausalConcept.ANOMALY],
        uncertainty_bps=_mean(
            states[CausalConcept.ANOMALY],
            states[CausalConcept.STRUCTURAL_FRAGILITY],
            states[CausalConcept.REGIME_TRANSITION],
            states[CausalConcept.LEADER_DIVERGENCE],
        ),
        opposite_pressure_bps=max(
            states[CausalConcept.FAILED_AUCTION],
            states[CausalConcept.MOMENTUM_DECAY],
            states[CausalConcept.ABSORPTION],
        ),
    )


def _quantile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("regime source-only calibration requires values")
    index = int(round((len(ordered) - 1) * fraction))
    return ordered[max(0, min(len(ordered) - 1, index))]


def _strict_three(values: list[int]) -> tuple[int, int, int]:
    distinct = sorted(set(values))
    if len(distinct) < 3:
        raise ValueError("regime calibration lacks velocity diversity")
    low = _quantile(distinct, 0.60)
    middle = _quantile(distinct, 0.75)
    high = _quantile(distinct, 0.90)
    candidates = sorted(set((low, middle, high)))
    if len(candidates) == 3:
        return candidates[0], candidates[1], candidates[2]
    low_index = max(0, len(distinct) * 3 // 5 - 1)
    mid_index = max(low_index + 1, len(distinct) * 3 // 4 - 1)
    high_index = max(mid_index + 1, len(distinct) * 9 // 10 - 1)
    high_index = min(high_index, len(distinct) - 1)
    if not distinct[low_index] < distinct[mid_index] < distinct[high_index]:
        return distinct[-3], distinct[-2], distinct[-1]
    return distinct[low_index], distinct[mid_index], distinct[high_index]


def _strict_two(values: list[int]) -> tuple[int, int]:
    distinct = sorted(set(values))
    if len(distinct) < 2:
        raise ValueError("regime calibration lacks pressure diversity")
    low = _quantile(distinct, 0.75)
    high = _quantile(distinct, 0.90)
    if low < high:
        return low, high
    return distinct[-2], distinct[-1]


def _policy_fingerprint(policy: DynamicTransitionPolicy) -> str:
    raw = json.dumps(asdict(policy), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def freeze_policy(*, r8_paths: dict[str, Path]) -> dict[str, Any]:
    rows = _aligned_source_rows(
        r8_paths,
        partition="r8",
        require_future=False,
    )
    transitions = tuple(
        _transition_observation(source, states)
        for source, states, _pre, _future in rows
    )
    history: deque[MarketTransitionObservation] = deque(
        maxlen=SEQUENCE_WINDOW
    )
    trajectory_rows = []
    for item in transitions:
        history.append(item)
        if len(history) < SEQUENCE_WINDOW:
            continue
        trajectory_rows.append(assess_market_trajectory(tuple(history)))

    deterioration_velocities = [
        item.deterioration_velocity_bps for item in trajectory_rows
    ]
    recovery_velocities = [
        item.recovery_velocity_bps for item in trajectory_rows
    ]
    pressures = [item.deterioration_pressure_bps for item in trajectory_rows]
    supports = [item.support_bps for item in trajectory_rows]
    persistences = [
        max(
            item.deterioration_persistence_bps,
            item.recovery_persistence_bps,
        )
        for item in trajectory_rows
    ]
    weakening, deterioration, failure = _strict_three(
        deterioration_velocities
    )
    deterioration_pressure, failure_pressure = _strict_two(pressures)

    policy = DynamicTransitionPolicy(
        minimum_observations=SEQUENCE_WINDOW,
        minimum_integrity_bps=9_500,
        weakening_velocity_bps=weakening,
        deterioration_velocity_bps=deterioration,
        failure_velocity_bps=failure,
        deterioration_pressure_bps=deterioration_pressure,
        failure_pressure_bps=failure_pressure,
        divergence_confirmation_bps=_quantile(
            [item.cross_market_confirmation_bps for item in transitions],
            0.25,
        ),
        divergence_correlation_bps=_quantile(
            [item.correlation_stability_bps for item in transitions],
            0.25,
        ),
        recovery_velocity_bps=_quantile(recovery_velocities, 0.75),
        recovery_support_bps=_quantile(supports, 0.60),
        persistence_bps=_quantile(persistences, 0.60),
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "mode": "SOURCE_ONLY_POLICY_FREEZE",
        "policy": asdict(policy),
        "policy_fingerprint": _policy_fingerprint(policy),
        "r8_source_observation_count": len(transitions),
        "r8_trajectory_count": len(trajectory_rows),
        "future_market_data_read_for_freeze": False,
        "future_outcomes_read_for_freeze": False,
        "trade_pnl_used": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }


def _policy_from_payload(payload: dict[str, Any]) -> DynamicTransitionPolicy:
    policy = DynamicTransitionPolicy(**payload["policy"])
    if _policy_fingerprint(policy) != payload["policy_fingerprint"]:
        raise ValueError("frozen STI-5 policy fingerprint mismatch")
    return policy


def _ratio_bps(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def _evaluate_partition(
    *,
    partition: str,
    paths: dict[str, Path],
    policy: DynamicTransitionPolicy,
) -> dict[str, Any]:
    rows = _aligned_source_rows(paths, partition=partition, require_future=True)
    history: deque[MarketTransitionObservation] = deque(
        maxlen=policy.minimum_observations
    )
    sample_count = 0
    warning_count = 0
    target_count = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    state_counts: dict[str, int] = {}
    first_source = None
    last_source = None
    last_target = None

    warning_states = {
        SharedRegimeTransitionState.EXHAUSTION_RISK,
        SharedRegimeTransitionState.TRANSITION_DEVELOPING,
        SharedRegimeTransitionState.REVERSAL_RISK,
        SharedRegimeTransitionState.REGIME_BREAK,
        SharedRegimeTransitionState.STRUCTURAL_DECOUPLING,
    }

    for source, states, pre, future in rows:
        if future is None:
            raise AssertionError("STI-5 evaluation requires future evidence")
        transition = _transition_observation(source, states)
        history.append(transition)
        assessment = assess_shared_regime_transition(
            tuple(history),
            policy=policy,
            expected_horizon="30M_RESEARCH",
        )
        state_counts[assessment.state.value] = (
            state_counts.get(assessment.state.value, 0) + 1
        )
        warning = assessment.state in warning_states

        target_states = _target_state(pre, future)
        future_transition = max(
            target_states[CausalConcept.REVERSAL],
            target_states[CausalConcept.STRUCTURAL_FAILURE],
            target_states[CausalConcept.ANOMALY],
        ) >= FUTURE_TRANSITION_TARGET_BPS

        sample_count += 1
        warning_count += int(warning)
        target_count += int(future_transition)
        if warning and future_transition:
            true_positive += 1
        elif warning and not future_transition:
            false_positive += 1
        elif not warning and future_transition:
            false_negative += 1
        else:
            true_negative += 1

        source_at = source.as_of
        target_at = _parse_key(future["NAS100"][-1].closed_key)
        first_source = source_at if first_source is None else first_source
        last_source = source_at
        last_target = target_at

    precision = _ratio_bps(true_positive, true_positive + false_positive)
    recall = _ratio_bps(true_positive, true_positive + false_negative)
    f1 = (
        0
        if precision + recall == 0
        else 2 * precision * recall // (precision + recall)
    )
    false_alert_rate = _ratio_bps(
        false_positive,
        true_positive + false_positive,
    )
    missed_rate = _ratio_bps(
        false_negative,
        true_positive + false_negative,
    )
    gate_pass = (
        precision >= MIN_PRECISION_BPS
        and recall >= MIN_RECALL_BPS
        and false_alert_rate <= MAX_FALSE_ALERT_RATE_BPS
        and missed_rate <= MAX_MISSED_TRANSITION_RATE_BPS
    )
    return {
        "partition": partition,
        "sample_count": sample_count,
        "warning_count": warning_count,
        "future_transition_target_count": target_count,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision_bps": precision,
        "recall_bps": recall,
        "f1_bps": f1,
        "false_transition_rate_bps": false_alert_rate,
        "missed_transition_rate_bps": missed_rate,
        "warning_density_bps": _ratio_bps(warning_count, sample_count),
        "state_counts": dict(sorted(state_counts.items())),
        "source_min": None if first_source is None else first_source.isoformat(),
        "source_max": None if last_source is None else last_source.isoformat(),
        "target_max": None if last_target is None else last_target.isoformat(),
        "gate_pass": gate_pass,
    }


def evaluate(
    *,
    policy_payload: dict[str, Any],
    evidence: dict[str, dict[str, Path]],
) -> dict[str, Any]:
    policy = _policy_from_payload(policy_payload)
    evaluations = {
        partition: _evaluate_partition(
            partition=partition,
            paths=evidence[partition],
            policy=policy,
        )
        for partition in PARTITIONS
    }
    temporal_order_pass = (
        evaluations["r8"]["target_max"] < evaluations["r6"]["source_min"]
        and evaluations["r6"]["target_max"] < evaluations["r5"]["source_min"]
    )
    consumed_gate_pass = (
        evaluations["r6"]["gate_pass"]
        and evaluations["r5"]["gate_pass"]
        and temporal_order_pass
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "mode": "CAUSAL_HISTORICAL_REPLAY",
        "engine_state": (
            "ENGINE_IMPLEMENTED_REAL_DATA_BOUND_CAUSAL_REPLAY_EXECUTED"
        ),
        "value_status": (
            "VALUE_DEMONSTRATED_CONSUMED_R6_R5"
            if consumed_gate_pass
            else "STI5_V1_FALSIFIED_ON_CONSUMED_EVIDENCE"
        ),
        "policy_fingerprint": _policy_fingerprint(policy),
        "future_transition_target_bps": FUTURE_TRANSITION_TARGET_BPS,
        "frozen_gates": {
            "minimum_precision_bps": MIN_PRECISION_BPS,
            "minimum_recall_bps": MIN_RECALL_BPS,
            "maximum_false_transition_rate_bps": MAX_FALSE_ALERT_RATE_BPS,
            "maximum_missed_transition_rate_bps": (
                MAX_MISSED_TRANSITION_RATE_BPS
            ),
        },
        "evaluations": evaluations,
        "temporal_order_pass": temporal_order_pass,
        "consumed_gate_pass": consumed_gate_pass,
        "source_only_engine": True,
        "future_data_used_for_intelligence": False,
        "future_data_used_offline_for_evaluation": True,
        "trade_pnl_used": False,
        "trader_methodology_used": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("freeze", "evaluate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    for partition in PARTITIONS:
        parser.add_argument(f"--{partition}-nas", type=Path)
        parser.add_argument(f"--{partition}-sp", type=Path)
        parser.add_argument(f"--{partition}-us", type=Path)
    args = parser.parse_args()

    if args.mode == "freeze":
        if any(item is None for item in (args.r8_nas, args.r8_sp, args.r8_us)):
            raise SystemExit("freeze requires R8 NAS100/SP500/US30 evidence")
        payload = freeze_policy(r8_paths=_paths(args, "r8"))
    else:
        if args.policy is None:
            raise SystemExit("evaluate requires --policy")
        for partition in PARTITIONS:
            if any(
                item is None
                for item in (
                    getattr(args, f"{partition}_nas"),
                    getattr(args, f"{partition}_sp"),
                    getattr(args, f"{partition}_us"),
                )
            ):
                raise SystemExit(f"evaluate requires {partition} evidence")
        payload = evaluate(
            policy_payload=json.loads(args.policy.read_text()),
            evidence={
                partition: _paths(args, partition)
                for partition in PARTITIONS
            },
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "mode": payload["mode"],
                "engine_state": payload.get("engine_state"),
                "value_status": payload.get("value_status"),
                "consumed_gate_pass": payload.get("consumed_gate_pass"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
