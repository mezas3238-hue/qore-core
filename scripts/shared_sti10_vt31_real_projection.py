#!/usr/bin/env python3
"""Real source-time binding for STI-10 Trader Relevant Projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedConfidenceCalibrationState,
    SharedDirectionalHypothesis,
    SharedEpistemicState,
    SharedIntelligenceClass,
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderCapability,
    SharedTraderIntelligenceSnapshot,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence_lifecycle import (
    build_trader_relevant_projection,
)

IDENTITY = "QORE_SHARED_STI10_TRADER_RELEVANT_PROJECTION_REAL_BINDING_001"


def _support(value: int) -> SharedSupportState:
    if value >= 8_000:
        return SharedSupportState.STRONG
    if value >= 6_500:
        return SharedSupportState.ELEVATED
    if value >= 4_500:
        return SharedSupportState.MODERATE
    if value >= 2_500:
        return SharedSupportState.LOW
    return SharedSupportState.VERY_LOW


def _regime(value: int) -> SharedRegimeTransitionState:
    if value >= 8_000:
        return SharedRegimeTransitionState.REGIME_BREAK
    if value >= 6_500:
        return SharedRegimeTransitionState.TRANSITION_DEVELOPING
    if value >= 4_500:
        return SharedRegimeTransitionState.EXHAUSTION_RISK
    return SharedRegimeTransitionState.STABLE


def _snapshot(observation, partition: str, index: int) -> SharedTraderIntelligenceSnapshot:
    uncertainty = (
        (10_000 - observation.data_integrity_bps)
        + observation.anomaly_bps
        + observation.regime_transition_bps
    ) // 3
    confidence = 10_000 - uncertainty
    coherence = (
        observation.leader_confirmation_bps
        + (10_000 - observation.leader_divergence_bps)
    ) // 2
    stability = 10_000 - (
        observation.leader_divergence_bps
        + observation.regime_transition_bps
    ) // 2
    continuation = (
        observation.displacement_bps
        + observation.acceptance_bps
        + observation.momentum_persistence_bps
    ) // 3
    reversal = (
        observation.failed_auction_bps
        + observation.leader_divergence_bps
        + observation.momentum_decay_bps
    ) // 3
    failure = (
        observation.structural_fragility_bps
        + observation.liquidity_vacuum_bps
        + observation.regime_transition_bps
    ) // 3
    positive_tail = (
        observation.displacement_bps
        + observation.acceptance_bps
        + observation.leader_confirmation_bps
    ) // 3
    systemic = (
        observation.structural_fragility_bps
        + observation.anomaly_bps
        + observation.leader_divergence_bps
    ) // 3

    if observation.data_integrity_bps < 9_500:
        epistemic = SharedEpistemicState.INSUFFICIENT
    elif uncertainty >= 6_000:
        epistemic = SharedEpistemicState.UNCERTAIN
    elif min(continuation, reversal) >= 5_500:
        epistemic = SharedEpistemicState.CONTRADICTORY
    else:
        epistemic = SharedEpistemicState.PARTIALLY_KNOWN

    direction = (
        SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
        if observation.direction_sign > 0
        else SharedDirectionalHypothesis.BEARISH_HYPOTHESIS
    )
    return SharedTraderIntelligenceSnapshot(
        snapshot_id=f"sti10:{partition}:{index:06d}:{observation.observation_id}",
        observed_at=observation.as_of,
        evidence_cutoff_at=observation.evidence_cutoff_at,
        asset=observation.asset,
        canonical_instrument_id="NAS100",
        market_family="US_EQUITY_INDEX",
        trader_horizon="M1",
        world_state="SOURCE_TIME_PARTIAL_GLOBAL_WORLD",
        market_regime="SOURCE_DERIVED",
        macro_regime="GLOBAL_MACRO_NOT_BOUND",
        rates_state="RATES_NOT_BOUND_IN_A_LANE",
        usd_state="USD_NOT_BOUND_IN_A_LANE",
        liquidity_state=f"LIQUIDITY_{_support(observation.liquidity_vacuum_bps).value}",
        volatility_state=f"ANOMALY_{_support(observation.anomaly_bps).value}",
        commodity_state="COMMODITY_WORLD_PENDING_B",
        agricultural_state="AGRICULTURAL_WORLD_PENDING_B",
        cross_asset_state=f"PEER_{_support(coherence).value}",
        relationship_coherence=_support(coherence),
        relationship_stability=_support(stability),
        relationship_age_ms=None,
        directional_hypothesis=direction,
        continuation_support=_support(continuation),
        reversal_support=_support(reversal),
        failure_hazard=_support(failure),
        positive_tail_support=_support(positive_tail),
        systemic_stress=_support(systemic),
        regime_transition_state=_regime(observation.regime_transition_bps),
        epistemic_state=epistemic,
        uncertainty_bps=uncertainty,
        confidence_bps=confidence,
        confidence_calibration=SharedConfidenceCalibrationState.UNCALIBRATED,
        calibration_evidence_refs=(),
        data_quality_bps=observation.data_integrity_bps,
        data_freshness_ms=None,
        causal_maturity="SOURCE_TIME_OBSERVATION",
        supporting_evidence_refs=tuple(sorted(observation.provenance_refs)),
        contradicting_evidence_refs=(),
        missing_evidence=(
            "GLOBAL_MULTI_FAMILY_WORLD_PENDING_B",
            "RATES_MACRO_COMMODITY_FULL_BINDING_PENDING_B",
        ),
        provenance_refs=tuple(sorted(observation.provenance_refs)),
        observation_horizon="M1",
        expected_validity_horizon="INTRADAY",
        decay_horizon="NEXT_SOURCE_OBSERVATION",
    )


def _partition(paths: dict[str, Path], partition: str) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=f"sti10_{partition}",
        require_future=False,
    )
    capability = SharedTraderCapability(
        trader_id="VT31_NAS100",
        markets=("NAS100",),
        horizons=("M1",),
        supported_intelligence_classes=tuple(
            sorted(SharedIntelligenceClass, key=lambda item: item.value)
        ),
        open_position_monitoring_capability=True,
    )
    deterministic = 0
    projected = 0
    unchanged_truth = 0
    future_reads = 0

    for index, (observation, _states, _pre, future) in enumerate(rows):
        if future is not None:
            future_reads += 1
            continue
        snapshot = _snapshot(observation, partition, index)
        classes = capability.supported_intelligence_classes
        relevant = tuple(
            sorted(
                set(
                    observation.provenance_refs
                    + (
                        "sti10:source-world",
                        "sti10:vt31-relevance",
                    )
                )
            )
        )
        omitted = (
            "global-world:commodity-pending-b",
            "global-world:macro-rates-pending-b",
        )
        first = build_trader_relevant_projection(
            projection_id=f"projection:{partition}:{index:06d}",
            snapshot=snapshot,
            capability=capability,
            projected_at=observation.as_of,
            intelligence_classes=classes,
            relevant_fact_refs=relevant,
            omitted_fact_refs=omitted,
        )
        second = build_trader_relevant_projection(
            projection_id=first.projection_id,
            snapshot=snapshot,
            capability=capability,
            projected_at=observation.as_of,
            intelligence_classes=classes,
            relevant_fact_refs=relevant,
            omitted_fact_refs=omitted,
        )
        projected += 1
        deterministic += int(first == second)
        unchanged_truth += int(
            first.global_state_fingerprint == snapshot.fingerprint()
            and not first.projection_changes_global_truth
        )

    passed = (
        projected > 0
        and deterministic == projected
        and unchanged_truth == projected
        and future_reads == 0
    )
    return {
        "partition": partition,
        "source_observation_count": len(rows),
        "projection_count": projected,
        "deterministic_projection_count": deterministic,
        "global_truth_preserved_count": unchanged_truth,
        "future_read_count": future_reads,
        "pass": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def paths(name: str) -> dict[str, Path]:
        return {
            "NAS100": getattr(args, f"{name}_nas"),
            "SP500": getattr(args, f"{name}_sp"),
            "US30": getattr(args, f"{name}_us"),
        }

    results = {
        name: _partition(paths(name), name)
        for name in ("r6", "r5")
    }
    passed = all(bool(row["pass"]) for row in results.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "STI10_VT31_REAL_PROJECTION_BINDING_PASS"
            if passed
            else "STI10_VT31_REAL_PROJECTION_BINDING_FAIL"
        ),
        "results": results,
        "vt31_real_data_bound": passed,
        "projection_changes_global_truth": False,
        "trader_methodology_visible_to_shared": False,
        "execution_authority": False,
        "future_market_used": False,
        "future_outcome_used": False,
        "seven_trader_global_world_binding_complete": False,
        "sti10_completed_and_proven": False,
        "dependency": "B_GLOBAL_WORLD_MULTI_FAMILY_BINDING",
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
