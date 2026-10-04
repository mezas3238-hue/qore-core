from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_trajectory_intelligence import (
    SharedTrajectoryState,
    assess_trajectory_intelligence,
)

NOW = datetime(2026, 10, 4, 18, 0, tzinfo=UTC)


def _healthy() -> SharedOpportunitySourceObservation:
    return SharedOpportunitySourceObservation(
        observation_id="a1-chain-healthy",
        asset="NAS100",
        as_of=NOW,
        evidence_cutoff_at=NOW,
        direction_sign=1,
        data_integrity_bps=10_000,
        compression_bps=4_000,
        liquidity_accumulation_bps=5_000,
        failed_auction_bps=2_000,
        displacement_bps=6_000,
        acceptance_bps=8_000,
        absorption_bps=6_000,
        leader_confirmation_bps=8_500,
        leader_divergence_bps=1_500,
        momentum_persistence_bps=8_000,
        momentum_decay_bps=1_500,
        structural_fragility_bps=1_500,
        liquidity_vacuum_bps=1_500,
        regime_transition_bps=1_500,
        anomaly_bps=1_000,
        provenance_refs=("a1:source-only",),
    )


def _distressed() -> SharedOpportunitySourceObservation:
    return replace(
        _healthy(),
        observation_id="a1-chain-distressed",
        acceptance_bps=1_500,
        absorption_bps=1_000,
        leader_confirmation_bps=1_000,
        leader_divergence_bps=9_000,
        momentum_persistence_bps=1_000,
        momentum_decay_bps=9_000,
        structural_fragility_bps=9_000,
        liquidity_vacuum_bps=9_000,
        regime_transition_bps=9_000,
        anomaly_bps=9_000,
        provenance_refs=("a1:distressed-source-only",),
    )


def test_a1_chain_consumes_mc17_and_mc18_into_mc19() -> None:
    result = assess_trajectory_intelligence(_healthy())

    assert result.state is SharedTrajectoryState.NORMAL_ADVERSITY
    assert result.mc17_output_consumed is True
    assert result.mc18_output_consumed is True
    assert len(result.mc17_fingerprint) == 64
    assert len(result.mc18_fingerprint) == 64
    assert result.source_only is True
    assert result.future_market_used is False
    assert result.future_outcome_used is False


def test_a1_chain_distinguishes_structural_failure() -> None:
    result = assess_trajectory_intelligence(_distressed())

    assert result.state is SharedTrajectoryState.STRUCTURAL_FAILURE
    assert result.structural_hazard_bps >= 7_000
    assert result.recovery_capacity_bps < 3_500


def test_a1_chain_fails_to_insufficient_on_low_integrity() -> None:
    observation = replace(
        _healthy(),
        observation_id="a1-chain-insufficient",
        data_integrity_bps=9_000,
    )
    result = assess_trajectory_intelligence(observation)

    assert result.state is SharedTrajectoryState.INSUFFICIENT
    assert result.dominant_agency_mechanism is None


def test_upstream_change_is_observable_downstream() -> None:
    first = assess_trajectory_intelligence(_healthy())
    second = assess_trajectory_intelligence(
        replace(
            _healthy(),
            observation_id="a1-chain-causal-perturbation",
            leader_divergence_bps=8_500,
            structural_fragility_bps=7_500,
            liquidity_vacuum_bps=7_000,
            regime_transition_bps=7_500,
            anomaly_bps=6_500,
            provenance_refs=("a1:causal-perturbation",),
        )
    )

    assert first.mc17_fingerprint != second.mc17_fingerprint
    assert first.mc18_fingerprint != second.mc18_fingerprint
    assert first.fingerprint() != second.fingerprint()
    assert first.structural_hazard_bps != second.structural_hazard_bps


def test_a1_chain_has_no_trade_or_capital_authority() -> None:
    result = assess_trajectory_intelligence(_healthy())

    assert result.creates_trader_setup is False
    assert result.position_management_authority is False
    assert result.execution_authority is False
    assert result.risk_authority is False
    assert result.sizing_authority is False
    assert result.capital_authority is False
    assert result.scientifically_calibrated is False


def test_a1_chain_is_deterministic() -> None:
    first = assess_trajectory_intelligence(_healthy())
    second = assess_trajectory_intelligence(_healthy())

    assert first.fingerprint() == second.fingerprint()
