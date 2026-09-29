from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunityEnginePolicy,
    SharedOpportunitySourceObservation,
    assess_global_opportunity,
    opportunity_source_score_bps,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedDirectionalHypothesis,
    SharedOpportunityMaturity,
    SharedTraderIntelligenceValidationError,
)

T0 = datetime(2026, 9, 29, 22, 30, tzinfo=UTC)


def _observation(
    *,
    minute: int,
    direction_sign: int = 1,
    integrity: int = 10_000,
    displacement: int = 7_500,
    acceptance: int = 7_200,
    confirmation: int = 7_700,
    momentum: int = 7_600,
    failed_auction: int = 1_500,
    absorption: int = 2_000,
    divergence: int = 2_000,
    momentum_decay: int = 1_500,
    transition: int = 2_000,
    compression: int = 4_000,
    accumulation: int = 4_500,
    vacuum: int = 4_000,
    fragility: int = 2_000,
    anomaly: int = 1_500,
) -> SharedOpportunitySourceObservation:
    at = T0 + timedelta(minutes=minute)
    return SharedOpportunitySourceObservation(
        observation_id=f"obs-{minute}",
        asset="NAS100",
        as_of=at,
        evidence_cutoff_at=at,
        direction_sign=direction_sign,
        data_integrity_bps=integrity,
        compression_bps=compression,
        liquidity_accumulation_bps=accumulation,
        failed_auction_bps=failed_auction,
        displacement_bps=displacement,
        acceptance_bps=acceptance,
        absorption_bps=absorption,
        leader_confirmation_bps=confirmation,
        leader_divergence_bps=divergence,
        momentum_persistence_bps=momentum,
        momentum_decay_bps=momentum_decay,
        structural_fragility_bps=fragility,
        liquidity_vacuum_bps=vacuum,
        regime_transition_bps=transition,
        anomaly_bps=anomaly,
        provenance_refs=("immutable-r8-source",),
    )


def _policy() -> SharedOpportunityEnginePolicy:
    return SharedOpportunityEnginePolicy(
        policy_id="sti2-r8-source-only-v1",
        version="001",
        frozen_at=T0,
        early_threshold_bps=5_000,
        developing_threshold_bps=6_000,
        mature_threshold_bps=7_000,
        minimum_integrity_bps=7_500,
        mature_persistence_bps=6_000,
        sequence_window=4,
        source_only_calibration=True,
        calibration_evidence_refs=("r8-source-only-score-distribution",),
    )


def test_engine_derives_mature_bullish_attention_without_trade_authority() -> None:
    observations = tuple(_observation(minute=i) for i in range(4))
    assessment = assess_global_opportunity(observations, policy=_policy())

    assert assessment.maturity is SharedOpportunityMaturity.MATURE
    assert assessment.directional_hypothesis is (
        SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
    )
    assert assessment.creates_trader_setup is False
    assert assessment.execution_authority is False
    assert assessment.sizing_authority is False
    assert assessment.capital_authority is False
    assert assessment.risk_authority is False
    assert len(assessment.policy_fingerprint) == 64


def test_engine_can_return_no_material_opportunity() -> None:
    observations = tuple(
        _observation(
            minute=i,
            displacement=1_000,
            acceptance=1_000,
            confirmation=2_000,
            momentum=1_000,
            compression=1_500,
            accumulation=1_500,
            vacuum=1_500,
            fragility=6_000,
            anomaly=5_000,
        )
        for i in range(4)
    )
    assessment = assess_global_opportunity(observations, policy=_policy())

    assert assessment.maturity is SharedOpportunityMaturity.NO_OPPORTUNITY
    assert assessment.directional_hypothesis is (
        SharedDirectionalHypothesis.INSUFFICIENT
    )


def test_engine_fails_to_insufficient_when_data_integrity_is_bad() -> None:
    observations = tuple(
        _observation(minute=i, integrity=7_000) for i in range(4)
    )
    assessment = assess_global_opportunity(observations, policy=_policy())

    assert assessment.maturity is SharedOpportunityMaturity.INSUFFICIENT
    assert assessment.directional_hypothesis is (
        SharedDirectionalHypothesis.INSUFFICIENT
    )


def test_reversal_structure_is_derived_from_source_observation() -> None:
    observations = tuple(
        _observation(
            minute=i,
            direction_sign=1,
            displacement=2_000,
            acceptance=2_000,
            confirmation=2_000,
            momentum=2_000,
            failed_auction=8_500,
            absorption=8_000,
            divergence=8_000,
            momentum_decay=8_200,
            transition=8_000,
        )
        for i in range(4)
    )
    assessment = assess_global_opportunity(observations, policy=_policy())

    assert assessment.directional_hypothesis is (
        SharedDirectionalHypothesis.REVERSAL_HYPOTHESIS
    )
    assert assessment.reversal_support_bps > assessment.trend_support_bps


def test_policy_requires_source_only_calibration() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="calibration must be source-only",
    ):
        replace(_policy(), source_only_calibration=False)


def test_source_observation_rejects_future_or_outcome_information() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="causal research evidence only",
    ):
        replace(_observation(minute=0), future_market_used=True)

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="causal research evidence only",
    ):
        replace(_observation(minute=0), future_outcome_used=True)


def test_sequence_must_be_chronological_and_single_asset() -> None:
    first = _observation(minute=0)
    second = _observation(minute=1)

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="strictly chronological",
    ):
        assess_global_opportunity((second, first), policy=_policy())

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="one asset",
    ):
        assess_global_opportunity(
            (first, replace(second, asset="SP500")),
            policy=_policy(),
        )


def test_score_is_deterministic_for_same_source_observation() -> None:
    observation = _observation(minute=0)
    assert opportunity_source_score_bps(observation) == (
        opportunity_source_score_bps(observation)
    )
