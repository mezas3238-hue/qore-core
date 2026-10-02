from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedAlertLifecycle,
    SharedConfidenceCalibrationState,
    SharedDirectionalHypothesis,
    SharedEpistemicState,
    SharedIntelligenceClass,
    SharedOpportunityAlert,
    SharedOpportunityMaturity,
    SharedPositionObservationSubscription,
    SharedPositionSide,
    SharedPositionThesisDelta,
    SharedPositionThreatAlert,
    SharedPositionThreatLevel,
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderCapability,
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
    SharedTraderRelevantProjection,
    TraderSharedOpportunityAssessment,
    TraderSharedOpportunityDisposition,
)

NOW = datetime(2026, 9, 29, 20, 0, tzinfo=UTC)
EVIDENCE_AT = NOW - timedelta(seconds=1)
SHA = "a" * 64


def _snapshot() -> SharedTraderIntelligenceSnapshot:
    return SharedTraderIntelligenceSnapshot(
        snapshot_id="shared-snapshot-001",
        observed_at=NOW,
        evidence_cutoff_at=EVIDENCE_AT,
        asset="XAUUSD",
        canonical_instrument_id="canonical:XAUUSD",
        market_family="METALS",
        trader_horizon="D1",
        world_state="GLOBAL_TRANSITION",
        market_regime="TRENDING",
        macro_regime="DISINFLATIONARY",
        rates_state="REAL_RATES_FALLING",
        usd_state="USD_WEAKENING",
        liquidity_state="NORMAL",
        volatility_state="ELEVATED",
        commodity_state="METALS_FIRM",
        agricultural_state="INSUFFICIENT",
        cross_asset_state="COHERENT",
        relationship_coherence=SharedSupportState.STRONG,
        relationship_stability=SharedSupportState.ELEVATED,
        relationship_age_ms=86_400_000,
        directional_hypothesis=(
            SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
        ),
        continuation_support=SharedSupportState.ELEVATED,
        reversal_support=SharedSupportState.LOW,
        failure_hazard=SharedSupportState.MODERATE,
        positive_tail_support=SharedSupportState.ELEVATED,
        systemic_stress=SharedSupportState.MODERATE,
        regime_transition_state=(
            SharedRegimeTransitionState.TRANSITION_DEVELOPING
        ),
        epistemic_state=SharedEpistemicState.PARTIALLY_KNOWN,
        uncertainty_bps=3500,
        confidence_bps=6500,
        confidence_calibration=(
            SharedConfidenceCalibrationState.UNCALIBRATED
        ),
        calibration_evidence_refs=(),
        data_quality_bps=9800,
        data_freshness_ms=500,
        causal_maturity="TEMPORAL_DEPENDENCY",
        supporting_evidence_refs=(
            "fact:metals-breadth",
            "fact:real-rates",
            "fact:usd",
        ),
        contradicting_evidence_refs=("fact:volatility",),
        missing_evidence=("missing:certified-causal-edge",),
        provenance_refs=(
            "graph:global-001",
            "snapshot:world-001",
        ),
        observation_horizon="H4",
        expected_validity_horizon="2D-5D",
        decay_horizon="24H",
    )


def _opportunity() -> SharedOpportunityAlert:
    return SharedOpportunityAlert(
        alert_id="alert-opportunity-001",
        hypothesis_id="hypothesis-xauusd-001",
        snapshot_id="shared-snapshot-001",
        asset="XAUUSD",
        canonical_instrument_id="canonical:XAUUSD",
        created_at=NOW,
        updated_at=NOW,
        evidence_cutoff_at=EVIDENCE_AT,
        lifecycle=SharedAlertLifecycle.NEW,
        maturity=SharedOpportunityMaturity.DEVELOPING,
        directional_hypothesis=(
            SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
        ),
        expected_horizon="2D-5D",
        reason_codes=(
            "CROSS_MARKET_COHERENCE_RISING",
            "USD_REGIME_WEAKENING",
        ),
        evidence_refs=(
            "fact:real-rates",
            "fact:usd",
        ),
    )


def _subscription() -> SharedPositionObservationSubscription:
    return SharedPositionObservationSubscription(
        subscription_id="subscription-001",
        position_id="position-001",
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH",
        asset="XAUUSD",
        canonical_instrument_id="canonical:XAUUSD",
        side=SharedPositionSide.LONG,
        opened_at=NOW,
        original_shared_snapshot_id="shared-snapshot-entry-001",
        original_world_state="RISK_ON",
        original_regime="TRENDING",
        original_relationship_state="COHERENT",
        expected_horizon="2D-5D",
        relevant_sensors=("sensor:rates", "sensor:usd"),
        relevant_relationships=("relation:gold-rates",),
        relevant_factors=("factor:usd",),
    )


def _delta() -> SharedPositionThesisDelta:
    return SharedPositionThesisDelta(
        delta_id="delta-001",
        subscription_id="subscription-001",
        entry_snapshot_id="shared-snapshot-entry-001",
        current_snapshot_id="shared-snapshot-current-002",
        observed_at=NOW,
        evidence_cutoff_at=EVIDENCE_AT,
        world_state_delta_bps=-2500,
        regime_delta_bps=-2000,
        relationship_delta_bps=-4000,
        continuation_delta_bps=-3000,
        failure_hazard_delta_bps=3500,
        uncertainty_delta_bps=1500,
        systemic_stress_delta_bps=1000,
        threat_level=SharedPositionThreatLevel.ELEVATED,
        reason_codes=(
            "CROSS_MARKET_COHERENCE_BREAK",
            "RATES_SUPPORT_LOST",
        ),
        evidence_refs=(
            "fact:gold-rates-break",
            "fact:rates-reversal",
        ),
    )


def test_snapshot_is_cognition_only_and_deterministic() -> None:
    first = _snapshot()
    second = _snapshot()

    assert first.fingerprint() == second.fingerprint()
    assert first.execution_authority is False
    assert first.risk_authority is False
    assert first.sizing_authority is False
    assert first.capital_authority is False
    assert first.strategy_mutation_authority is False
    assert first.broker_mutation_authority is False


@pytest.mark.parametrize(
    "authority_field",
    (
        "execution_authority",
        "risk_authority",
        "sizing_authority",
        "capital_authority",
        "strategy_mutation_authority",
        "broker_mutation_authority",
    ),
)
def test_snapshot_rejects_every_sovereign_authority(
    authority_field: str,
) -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot carry sovereign authority",
    ):
        replace(_snapshot(), **{authority_field: True})


def test_snapshot_rejects_future_evidence() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="future Shared evidence is forbidden",
    ):
        replace(
            _snapshot(),
            evidence_cutoff_at=NOW + timedelta(microseconds=1),
        )


def test_calibrated_confidence_requires_calibration_evidence() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="requires calibration evidence",
    ):
        replace(
            _snapshot(),
            confidence_calibration=(
                SharedConfidenceCalibrationState.CALIBRATED
            ),
        )

    calibrated = replace(
        _snapshot(),
        confidence_calibration=SharedConfidenceCalibrationState.CALIBRATED,
        calibration_evidence_refs=("calibration:shared-sti-001",),
    )
    assert calibrated.confidence_bps == 6500


def test_uncalibrated_support_cannot_claim_calibration_evidence() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="uncalibrated confidence cannot carry calibration evidence",
    ):
        replace(
            _snapshot(),
            calibration_evidence_refs=("calibration:not-authorized",),
        )


def test_opportunity_is_attention_not_trader_setup_or_order() -> None:
    alert = _opportunity()

    assert alert.attention_only is True
    assert alert.creates_trader_setup is False
    assert alert.execution_authority is False
    assert alert.sizing_authority is False
    assert alert.capital_authority is False
    assert alert.risk_authority is False
    assert alert.broker_mutation_authority is False
    assert len(alert.fingerprint()) == 64

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="attention, never a Trader setup",
    ):
        replace(alert, creates_trader_setup=True)


def test_empty_or_insufficient_opportunity_is_legal() -> None:
    no_opportunity = replace(
        _opportunity(),
        maturity=SharedOpportunityMaturity.NO_OPPORTUNITY,
        directional_hypothesis=SharedDirectionalHypothesis.INSUFFICIENT,
        reason_codes=("NO_MATERIAL_OPPORTUNITY",),
    )
    insufficient = replace(
        _opportunity(),
        maturity=SharedOpportunityMaturity.INSUFFICIENT,
        directional_hypothesis=SharedDirectionalHypothesis.INSUFFICIENT,
        reason_codes=("INSUFFICIENT_EVIDENCE",),
    )

    assert no_opportunity.maturity is SharedOpportunityMaturity.NO_OPPORTUNITY
    assert insufficient.maturity is SharedOpportunityMaturity.INSUFFICIENT


def test_trader_can_abstain_from_strong_shared_opportunity() -> None:
    alert = replace(
        _opportunity(),
        maturity=SharedOpportunityMaturity.MATURE,
    )
    assessment = TraderSharedOpportunityAssessment(
        alert_id=alert.alert_id,
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH",
        assessed_at=NOW,
        disposition=TraderSharedOpportunityDisposition.ABSTAIN,
        methodology_validated=False,
        evidence_refs=("trader:geometry-invalid",),
    )

    assert alert.maturity is SharedOpportunityMaturity.MATURE
    assert assessment.disposition is TraderSharedOpportunityDisposition.ABSTAIN
    assert assessment.execution_instruction is False


def test_valid_trade_requires_trader_methodology_validation() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="requires Trader methodology validation",
    ):
        TraderSharedOpportunityAssessment(
            alert_id="alert-opportunity-001",
            trader_id="TRADER-001",
            assessed_at=NOW,
            disposition=TraderSharedOpportunityDisposition.VALID_TRADE,
            methodology_validated=False,
            evidence_refs=("trader:review",),
        )


def test_position_subscription_is_read_only() -> None:
    subscription = _subscription()

    assert subscription.read_only is True
    assert subscription.position_management_authority is False

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot manage the position",
    ):
        replace(
            subscription,
            position_management_authority=True,
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "mandatory_exit",
        "mandatory_stop_change",
        "mandatory_target_change",
        "execution_authority",
    ),
)
def test_position_delta_cannot_command_management(field_name: str) -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot command position management",
    ):
        replace(_delta(), **{field_name: True})


def test_position_delta_rejects_future_evidence() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot use future evidence",
    ):
        replace(
            _delta(),
            evidence_cutoff_at=NOW + timedelta(seconds=1),
        )


def test_position_threat_is_evidence_not_exit_or_risk_command() -> None:
    alert = SharedPositionThreatAlert(
        alert_id="position-alert-001",
        hypothesis_id="position-hypothesis-001",
        delta_id="delta-001",
        position_id="position-001",
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH",
        created_at=NOW,
        updated_at=NOW,
        evidence_cutoff_at=EVIDENCE_AT,
        lifecycle=SharedAlertLifecycle.NEW,
        threat_level=SharedPositionThreatLevel.HIGH,
        continuation_support=SharedSupportState.LOW,
        failure_hazard=SharedSupportState.STRONG,
        uncertainty_bps=3000,
        reason_codes=(
            "CROSS_MARKET_COHERENCE_BREAK",
            "RATES_SUPPORT_LOST",
        ),
        evidence_refs=(
            "fact:gold-rates-break",
            "fact:rates-reversal",
        ),
    )

    assert alert.forced_exit is False
    assert alert.forced_protection is False
    assert alert.trader_action_required is False
    assert alert.execution_authority is False
    assert alert.risk_authority is False
    assert len(alert.fingerprint()) == 64

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="evidence, never an action command",
    ):
        replace(alert, forced_exit=True)


def test_trader_capability_registry_is_routing_only() -> None:
    capability = SharedTraderCapability(
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH",
        markets=("XAUUSD",),
        horizons=("D1", "H4"),
        supported_intelligence_classes=(
            SharedIntelligenceClass.OPPORTUNITY,
            SharedIntelligenceClass.POSITION_THREAT,
        ),
        open_position_monitoring_capability=True,
    )

    assert capability.methodology_visible_to_shared is False
    assert capability.shared_methodology_mutation_authority is False

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot own Trader methodology",
    ):
        replace(capability, methodology_visible_to_shared=True)


def test_trader_projection_cannot_rewrite_global_truth() -> None:
    projection = SharedTraderRelevantProjection(
        projection_id="projection-001",
        snapshot_id="snapshot-world-001",
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH",
        projected_at=NOW,
        evidence_cutoff_at=EVIDENCE_AT,
        intelligence_classes=(
            SharedIntelligenceClass.OPPORTUNITY,
            SharedIntelligenceClass.REGIME_TRANSITION,
        ),
        relevant_fact_refs=(
            "fact:rates",
            "fact:usd",
        ),
        omitted_fact_refs=("fact:irrelevant-local-market",),
        global_state_fingerprint=SHA,
    )

    assert projection.projection_changes_global_truth is False
    assert projection.execution_authority is False

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot mutate global truth or execute",
    ):
        replace(projection, projection_changes_global_truth=True)


def test_projection_rejects_future_evidence() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot use future evidence",
    ):
        SharedTraderRelevantProjection(
            projection_id="projection-001",
            snapshot_id="snapshot-world-001",
            trader_id="TRADER-001",
            projected_at=NOW,
            evidence_cutoff_at=NOW + timedelta(seconds=1),
            intelligence_classes=(SharedIntelligenceClass.OPPORTUNITY,),
            relevant_fact_refs=(),
            omitted_fact_refs=(),
            global_state_fingerprint=SHA,
        )
