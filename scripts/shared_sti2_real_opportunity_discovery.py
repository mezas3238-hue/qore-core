#!/usr/bin/env python3
"""STI-2 real historical opportunity-discovery engine replay.

Freeze mode reads only source-time R8 evidence and freezes score thresholds.
Evaluate mode replays the frozen policy on immutable R8/R6/R5 evidence. Future
30-minute market states are attached only after each source-time intelligence
output has been created, for offline scientific scoring.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import (
    MARKETS,
    PRE_WINDOW_MINUTES,
    SAMPLE_MINUTES,
    TARGET_HORIZON_MINUTES,
    _load_bars,
    _metric,
    _parse_key,
    _regime,
    _sign,
    _source_state,
    _target_state,
)

from qore.infrastructure.core_stack_v2.dynamic_causal_graph import CausalConcept
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunityEngineAssessment,
    SharedOpportunityEnginePolicy,
    SharedOpportunitySourceObservation,
    assess_global_opportunity,
    opportunity_source_score_bps,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedAlertLifecycle,
    SharedConfidenceCalibrationState,
    SharedDirectionalHypothesis,
    SharedEpistemicState,
    SharedOpportunityAlert,
    SharedOpportunityMaturity,
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderIntelligenceSnapshot,
)

IDENTITY = "QORE_SHARED_STI2_REAL_GLOBAL_OPPORTUNITY_DISCOVERY_V1"
SCHEMA = "qore.shared.sti2.real_opportunity_discovery.v1"
PARTITIONS = ("r8", "r6", "r5")
FUTURE_MATERIAL_TARGET_BPS = 6_500
MIN_PRECISION_BPS = 5_500
MIN_RECALL_BPS = 4_000
MAX_FALSE_ALERT_RATE_BPS = 4_500
MAX_MISSED_OPPORTUNITY_RATE_BPS = 6_000


def _clamp_bps(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _support_state(value: int) -> SharedSupportState:
    if value >= 8_000:
        return SharedSupportState.STRONG
    if value >= 6_500:
        return SharedSupportState.ELEVATED
    if value >= 4_500:
        return SharedSupportState.MODERATE
    if value >= 2_500:
        return SharedSupportState.LOW
    return SharedSupportState.VERY_LOW


def _regime_transition_state(value: int) -> SharedRegimeTransitionState:
    if value >= 8_000:
        return SharedRegimeTransitionState.REGIME_BREAK
    if value >= 6_000:
        return SharedRegimeTransitionState.TRANSITION_DEVELOPING
    return SharedRegimeTransitionState.STABLE


def _source_direction(pre: dict[str, tuple[Any, ...]]) -> int:
    return _sign(_metric(pre["NAS100"][-15:]).net_bps)


def _build_source_observation(
    *,
    partition: str,
    source_at: Any,
    pre: dict[str, tuple[Any, ...]],
) -> tuple[SharedOpportunitySourceObservation, dict[CausalConcept, int]]:
    states, _vol_ratio, _coherence = _source_state(pre)
    observation = SharedOpportunitySourceObservation(
        observation_id=f"{partition}:NAS100:{source_at.isoformat()}",
        asset="NAS100",
        as_of=source_at,
        evidence_cutoff_at=source_at,
        direction_sign=_source_direction(pre),
        data_integrity_bps=10_000,
        compression_bps=states[CausalConcept.COMPRESSION],
        liquidity_accumulation_bps=states[
            CausalConcept.LIQUIDITY_ACCUMULATION
        ],
        failed_auction_bps=states[CausalConcept.FAILED_AUCTION],
        displacement_bps=states[CausalConcept.DISPLACEMENT],
        acceptance_bps=states[CausalConcept.ACCEPTANCE],
        absorption_bps=states[CausalConcept.ABSORPTION],
        leader_confirmation_bps=states[CausalConcept.LEADER_CONFIRMATION],
        leader_divergence_bps=states[CausalConcept.LEADER_DIVERGENCE],
        momentum_persistence_bps=states[CausalConcept.MOMENTUM_PERSISTENCE],
        momentum_decay_bps=states[CausalConcept.MOMENTUM_DECAY],
        structural_fragility_bps=states[CausalConcept.STRUCTURAL_FRAGILITY],
        liquidity_vacuum_bps=states[CausalConcept.LIQUIDITY_VACUUM],
        regime_transition_bps=states[CausalConcept.REGIME_TRANSITION],
        anomaly_bps=states[CausalConcept.ANOMALY],
        provenance_refs=(
            f"immutable-{partition}-NAS100-SP500-US30-M1",
            "shared-wp03-source-state",
        ),
    )
    return observation, states


def _aligned_source_rows(
    evidence_paths: dict[str, Path],
    *,
    partition: str,
    require_future: bool,
) -> tuple[
    tuple[
        SharedOpportunitySourceObservation,
        dict[CausalConcept, int],
        dict[str, tuple[Any, ...]],
        dict[str, tuple[Any, ...]] | None,
    ],
    ...,
]:
    bars = {market: _load_bars(evidence_paths[market]) for market in MARKETS}
    peer_indexes = {
        market: {bar.closed_key: index for index, bar in enumerate(bars[market])}
        for market in ("SP500", "US30")
    }
    rows: list[
        tuple[
            SharedOpportunitySourceObservation,
            dict[CausalConcept, int],
            dict[str, tuple[Any, ...]],
            dict[str, tuple[Any, ...]] | None,
        ]
    ] = []
    nas = bars["NAS100"]
    end_guard = TARGET_HORIZON_MINUTES + 1 if require_future else 0
    for nas_index in range(PRE_WINDOW_MINUTES, len(nas) - end_guard):
        key = nas[nas_index].closed_key
        if int(key[14:16]) not in SAMPLE_MINUTES:
            continue

        indexes = {"NAS100": nas_index}
        missing = False
        for market in ("SP500", "US30"):
            index = peer_indexes[market].get(key)
            if index is None:
                missing = True
                break
            indexes[market] = index
        if missing:
            continue

        pre: dict[str, tuple[Any, ...]] = {}
        future: dict[str, tuple[Any, ...]] | None = {} if require_future else None
        complete = True
        for market in MARKETS:
            index = indexes[market]
            if index < PRE_WINDOW_MINUTES:
                complete = False
                break
            if require_future and index + TARGET_HORIZON_MINUTES >= len(bars[market]):
                complete = False
                break
            pre_rows = bars[market][
                index - PRE_WINDOW_MINUTES + 1 : index + 1
            ]
            if len(pre_rows) != PRE_WINDOW_MINUTES:
                complete = False
                break
            pre[market] = pre_rows
            if require_future and future is not None:
                future[market] = bars[market][
                    index + 1 : index + 1 + TARGET_HORIZON_MINUTES
                ]
        if not complete:
            continue

        source_at = _parse_key(pre["NAS100"][-1].closed_key)
        observation, states = _build_source_observation(
            partition=partition,
            source_at=source_at,
            pre=pre,
        )
        rows.append((observation, states, pre, future))

    return tuple(rows)


def _strict_source_quantiles(scores: list[int]) -> tuple[int, int, int]:
    distinct = sorted(set(scores))
    if len(distinct) < 4:
        raise ValueError("source-only opportunity calibration lacks score diversity")

    def pick(fraction: float) -> int:
        index = int(round((len(distinct) - 1) * fraction))
        return distinct[max(0, min(len(distinct) - 1, index))]

    early = pick(0.60)
    developing = pick(0.75)
    mature = pick(0.90)
    if not early < developing < mature:
        early = distinct[max(0, len(distinct) * 3 // 5 - 1)]
        developing = distinct[max(1, len(distinct) * 3 // 4 - 1)]
        mature = distinct[max(2, len(distinct) * 9 // 10 - 1)]
    if not early < developing < mature:
        raise ValueError("unable to freeze strict source-only thresholds")
    return early, developing, mature


def freeze_policy(
    *,
    r8_paths: dict[str, Path],
) -> dict[str, Any]:
    rows = _aligned_source_rows(
        r8_paths,
        partition="r8",
        require_future=False,
    )
    observations = [item[0] for item in rows]
    scores = [opportunity_source_score_bps(item) for item in observations]
    early, developing, mature = _strict_source_quantiles(scores)
    frozen_at = max(item.as_of for item in observations)
    policy = SharedOpportunityEnginePolicy(
        policy_id="QORE_SHARED_STI2_SOURCE_ONLY_POLICY_V1",
        version="001",
        frozen_at=frozen_at,
        early_threshold_bps=early,
        developing_threshold_bps=developing,
        mature_threshold_bps=mature,
        minimum_integrity_bps=9_500,
        mature_persistence_bps=6_000,
        sequence_window=4,
        source_only_calibration=True,
        calibration_evidence_refs=(
            "immutable-r8-source-only-score-distribution",
            "no-target-or-outcome-used-for-threshold-freeze",
        ),
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "mode": "SOURCE_ONLY_POLICY_FREEZE",
        "policy": {
            "policy_id": policy.policy_id,
            "version": policy.version,
            "frozen_at": policy.frozen_at.isoformat(),
            "early_threshold_bps": policy.early_threshold_bps,
            "developing_threshold_bps": policy.developing_threshold_bps,
            "mature_threshold_bps": policy.mature_threshold_bps,
            "minimum_integrity_bps": policy.minimum_integrity_bps,
            "mature_persistence_bps": policy.mature_persistence_bps,
            "sequence_window": policy.sequence_window,
            "source_only_calibration": policy.source_only_calibration,
            "calibration_evidence_refs": policy.calibration_evidence_refs,
            "fingerprint": policy.fingerprint(),
        },
        "r8_source_observation_count": len(observations),
        "source_score_min_bps": min(scores),
        "source_score_max_bps": max(scores),
        "future_market_data_read_for_freeze": False,
        "future_outcomes_read_for_freeze": False,
        "trade_pnl_used": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }


def _policy_from_payload(payload: dict[str, Any]) -> SharedOpportunityEnginePolicy:
    row = payload["policy"]
    policy = SharedOpportunityEnginePolicy(
        policy_id=str(row["policy_id"]),
        version=str(row["version"]),
        frozen_at=_parse_key(str(row["frozen_at"])[:19]),
        early_threshold_bps=int(row["early_threshold_bps"]),
        developing_threshold_bps=int(row["developing_threshold_bps"]),
        mature_threshold_bps=int(row["mature_threshold_bps"]),
        minimum_integrity_bps=int(row["minimum_integrity_bps"]),
        mature_persistence_bps=int(row["mature_persistence_bps"]),
        sequence_window=int(row["sequence_window"]),
        source_only_calibration=bool(row["source_only_calibration"]),
        calibration_evidence_refs=tuple(row["calibration_evidence_refs"]),
    )
    if policy.fingerprint() != row["fingerprint"]:
        raise ValueError("frozen STI-2 policy fingerprint mismatch")
    return policy


def _build_snapshot_and_alert(
    *,
    partition: str,
    assessment: SharedOpportunityEngineAssessment,
    observation: SharedOpportunitySourceObservation,
    states: dict[CausalConcept, int],
    policy: SharedOpportunityEnginePolicy,
) -> SharedOpportunityAlert | None:
    if assessment.maturity in {
        SharedOpportunityMaturity.NO_OPPORTUNITY,
        SharedOpportunityMaturity.INSUFFICIENT,
    }:
        return None

    direction = (
        SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
        if observation.direction_sign > 0
        else SharedDirectionalHypothesis.BEARISH_HYPOTHESIS
        if observation.direction_sign < 0
        else SharedDirectionalHypothesis.INSUFFICIENT
    )
    uncertainty = _clamp_bps(assessment.uncertainty_bps)
    snapshot = SharedTraderIntelligenceSnapshot(
        snapshot_id=f"sti2:{observation.observation_id}",
        observed_at=observation.as_of,
        evidence_cutoff_at=observation.evidence_cutoff_at,
        asset="NAS100",
        canonical_instrument_id="canonical:NAS100",
        market_family="EQUITY_INDEX",
        trader_horizon="M30_RESEARCH",
        world_state=_regime(states),
        market_regime=_regime(states),
        macro_regime="INSUFFICIENT",
        rates_state="INSUFFICIENT",
        usd_state="INSUFFICIENT",
        liquidity_state=(
            "STRESSED"
            if states[CausalConcept.LIQUIDITY_VACUUM] >= 6_500
            else "NORMAL"
        ),
        volatility_state=(
            "TRANSITION"
            if states[CausalConcept.REGIME_TRANSITION] >= 6_000
            else "STABLE"
        ),
        commodity_state="INSUFFICIENT",
        agricultural_state="INSUFFICIENT",
        cross_asset_state=(
            "COHERENT"
            if states[CausalConcept.LEADER_CONFIRMATION] >= 6_000
            else "DIVERGENT"
        ),
        relationship_coherence=_support_state(
            states[CausalConcept.LEADER_CONFIRMATION]
        ),
        relationship_stability=_support_state(
            10_000 - states[CausalConcept.LEADER_DIVERGENCE]
        ),
        relationship_age_ms=0,
        directional_hypothesis=direction,
        continuation_support=_support_state(
            states[CausalConcept.MOMENTUM_PERSISTENCE]
        ),
        reversal_support=_support_state(
            max(
                states[CausalConcept.MOMENTUM_DECAY],
                states[CausalConcept.FAILED_AUCTION],
            )
        ),
        failure_hazard=_support_state(
            states[CausalConcept.STRUCTURAL_FRAGILITY]
        ),
        positive_tail_support=_support_state(
            max(
                states[CausalConcept.DISPLACEMENT],
                states[CausalConcept.ACCEPTANCE],
            )
        ),
        systemic_stress=_support_state(states[CausalConcept.ANOMALY]),
        regime_transition_state=_regime_transition_state(
            states[CausalConcept.REGIME_TRANSITION]
        ),
        epistemic_state=SharedEpistemicState.PARTIALLY_KNOWN,
        uncertainty_bps=uncertainty,
        confidence_bps=10_000 - uncertainty,
        confidence_calibration=SharedConfidenceCalibrationState.UNCALIBRATED,
        calibration_evidence_refs=(),
        data_quality_bps=observation.data_integrity_bps,
        data_freshness_ms=0,
        causal_maturity="SOURCE_ONLY_RESEARCH",
        supporting_evidence_refs=observation.provenance_refs,
        contradicting_evidence_refs=(
            ("structural-fragility-high",)
            if states[CausalConcept.STRUCTURAL_FRAGILITY] >= 6_000
            else ()
        ),
        missing_evidence=(
            "macro-world-not-bound-in-sti2-v1",
            "rates-world-not-bound-in-sti2-v1",
        ),
        provenance_refs=observation.provenance_refs,
        observation_horizon="M1_TO_H1_SOURCE_WINDOW",
        expected_validity_horizon="30M_RESEARCH",
        decay_horizon="30M",
    )
    evidence_refs = tuple(
        sorted(
            (
                observation.observation_id,
                f"policy:{policy.fingerprint()}",
                f"snapshot:{snapshot.fingerprint()}",
            )
        )
    )
    return SharedOpportunityAlert(
        alert_id=f"sti2-alert:{partition}:{observation.as_of.isoformat()}",
        hypothesis_id=f"sti2-hypothesis:{observation.as_of.isoformat()}",
        snapshot_id=snapshot.snapshot_id,
        asset="NAS100",
        canonical_instrument_id="canonical:NAS100",
        created_at=observation.as_of,
        updated_at=observation.as_of,
        evidence_cutoff_at=observation.evidence_cutoff_at,
        lifecycle=SharedAlertLifecycle.NEW,
        maturity=assessment.maturity,
        directional_hypothesis=assessment.directional_hypothesis,
        expected_horizon="30M_RESEARCH",
        reason_codes=assessment.reason_codes,
        evidence_refs=evidence_refs,
    )


def _ratio_bps(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return numerator * 10_000 // denominator


def _evaluate_partition(
    *,
    partition: str,
    paths: dict[str, Path],
    policy: SharedOpportunityEnginePolicy,
) -> dict[str, Any]:
    rows = _aligned_source_rows(paths, partition=partition, require_future=True)
    history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=policy.sequence_window
    )
    sample_count = 0
    attention_count = 0
    material_alert_count = 0
    mature_count = 0
    target_count = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    generated_alert_count = 0
    first_source = None
    last_source = None
    last_target = None

    for observation, states, pre, future in rows:
        if future is None:
            raise AssertionError("evaluation row requires future evidence")
        history.append(observation)
        assessment = assess_global_opportunity(tuple(history), policy=policy)
        alert = _build_snapshot_and_alert(
            partition=partition,
            assessment=assessment,
            observation=observation,
            states=states,
            policy=policy,
        )
        generated_alert_count += int(alert is not None)

        target_states = _target_state(pre, future)
        future_material = max(
            target_states[CausalConcept.EXPANSION_READINESS],
            target_states[CausalConcept.DISPLACEMENT],
            target_states[CausalConcept.CONTINUATION],
            target_states[CausalConcept.REVERSAL],
        ) >= FUTURE_MATERIAL_TARGET_BPS
        attention = assessment.maturity in {
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.MATURE,
            SharedOpportunityMaturity.DETERIORATING,
        }
        material_alert = assessment.maturity in {
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.MATURE,
        }

        sample_count += 1
        attention_count += int(attention)
        material_alert_count += int(material_alert)
        mature_count += int(
            assessment.maturity is SharedOpportunityMaturity.MATURE
        )
        target_count += int(future_material)

        if material_alert and future_material:
            true_positive += 1
        elif material_alert and not future_material:
            false_positive += 1
        elif not material_alert and future_material:
            false_negative += 1
        else:
            true_negative += 1

        source_at = observation.as_of
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
        and missed_rate <= MAX_MISSED_OPPORTUNITY_RATE_BPS
    )

    return {
        "partition": partition,
        "sample_count": sample_count,
        "attention_count": attention_count,
        "material_alert_count": material_alert_count,
        "mature_count": mature_count,
        "generated_alert_count": generated_alert_count,
        "future_material_target_count": target_count,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision_bps": precision,
        "recall_bps": recall,
        "f1_bps": f1,
        "false_alert_rate_bps": false_alert_rate,
        "missed_opportunity_rate_bps": missed_rate,
        "attention_coverage_bps": _ratio_bps(attention_count, sample_count),
        "material_alert_density_bps": _ratio_bps(
            material_alert_count,
            sample_count,
        ),
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
            else "STI2_V1_FALSIFIED_ON_CONSUMED_EVIDENCE"
        ),
        "policy_fingerprint": policy.fingerprint(),
        "future_material_target_bps": FUTURE_MATERIAL_TARGET_BPS,
        "frozen_gates": {
            "minimum_precision_bps": MIN_PRECISION_BPS,
            "minimum_recall_bps": MIN_RECALL_BPS,
            "maximum_false_alert_rate_bps": MAX_FALSE_ALERT_RATE_BPS,
            "maximum_missed_opportunity_rate_bps": (
                MAX_MISSED_OPPORTUNITY_RATE_BPS
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


def _paths(args: argparse.Namespace, partition: str) -> dict[str, Path]:
    return {
        "NAS100": getattr(args, f"{partition}_nas"),
        "SP500": getattr(args, f"{partition}_sp"),
        "US30": getattr(args, f"{partition}_us"),
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
        required = (args.r8_nas, args.r8_sp, args.r8_us)
        if any(item is None for item in required):
            raise SystemExit("freeze requires R8 NAS100/SP500/US30 evidence")
        payload = freeze_policy(r8_paths=_paths(args, "r8"))
    else:
        if args.policy is None:
            raise SystemExit("evaluate requires --policy")
        for partition in PARTITIONS:
            required = (
                getattr(args, f"{partition}_nas"),
                getattr(args, f"{partition}_sp"),
                getattr(args, f"{partition}_us"),
            )
            if any(item is None for item in required):
                raise SystemExit(f"evaluate requires {partition} evidence")
        policy_payload = json.loads(args.policy.read_text())
        payload = evaluate(
            policy_payload=policy_payload,
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
