from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedConfidenceCalibrationState,
    SharedDirectionalHypothesis,
    SharedEpistemicState,
    SharedOpportunityMaturity,
    SharedPositionThreatLevel,
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence_research_policy import (
    SharedAlertMaterialityPolicy,
    SharedMaterialityDisposition,
    SharedPolicyCalibrationState,
    assess_snapshot_materiality,
    validate_continuation_support_state,
    validate_opportunity_maturity_transition,
    validate_position_threat_state,
    validate_regime_transition_state,
)

T0 = datetime(2026, 9, 29, 21, 0, tzinfo=UTC)


def _snapshot(
    *,
    snapshot_id: str,
    observed_at: datetime,
    confidence_bps: int = 6000,
    uncertainty_bps: int = 3000,
    data_quality_bps: int = 9900,
    world_state: str = "RISK_ON",
    market_regime: str = "TRENDING",
    hypothesis: SharedDirectionalHypothesis = (
        SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
    ),
    epistemic_state: SharedEpistemicState = (
        SharedEpistemicState.PARTIALLY_KNOWN
    ),
) -> SharedTraderIntelligenceSnapshot:
    return SharedTraderIntelligenceSnapshot(
        snapshot_id=snapshot_id,
        observed_at=observed_at,
        evidence_cutoff_at=observed_at - timedelta(milliseconds=1),
        asset="XAUUSD",
        canonical_instrument_id="canonical:XAUUSD",
        market_family="METALS",
        trader_horizon="D1",
        world_state=world_state,
        market_regime=market_regime,
        macro_regime="DISINFLATIONARY",
        rates_state="FALLING",
        usd_state="WEAKENING",
        liquidity_state="NORMAL",
        volatility_state="NORMAL",
        commodity_state="METALS_FIRM",
        agricultural_state="INSUFFICIENT",
        cross_asset_state="COHERENT",
        relationship_coherence=SharedSupportState.STRONG,
        relationship_stability=SharedSupportState.ELEVATED,
        relationship_age_ms=1_000,
        directional_hypothesis=hypothesis,
        continuation_support=SharedSupportState.ELEVATED,
        reversal_support=SharedSupportState.LOW,
        failure_hazard=SharedSupportState.LOW,
        positive_tail_support=SharedSupportState.ELEVATED,
        systemic_stress=SharedSupportState.LOW,
        regime_transition_state=SharedRegimeTransitionState.STABLE,
        epistemic_state=epistemic_state,
        uncertainty_bps=uncertainty_bps,
        confidence_bps=confidence_bps,
        confidence_calibration=(
            SharedConfidenceCalibrationState.UNCALIBRATED
        ),
        calibration_evidence_refs=(),
        data_quality_bps=data_quality_bps,
        data_freshness_ms=100,
        causal_maturity="TEMPORAL_DEPENDENCY",
        supporting_evidence_refs=("fact:rates", "fact:usd"),
        contradicting_evidence_refs=(),
        missing_evidence=("missing:causal-certification",),
        provenance_refs=("world:001",),
        observation_horizon="H4",
        expected_validity_horizon="2D-5D",
        decay_horizon="24H",
    )


def _policy() -> SharedAlertMaterialityPolicy:
    return SharedAlertMaterialityPolicy(
        policy_id="materiality-research-001",
        version="001",
        frozen_at=T0,
        calibration_state=SharedPolicyCalibrationState.PREREGISTERED,
        policy_evidence_refs=("preregistration:sti-materiality-001",),
        min_confidence_change_bps=500,
        min_uncertainty_change_bps=500,
        min_data_quality_change_bps=500,
        require_world_state_change=False,
        require_regime_state_change=False,
        require_directional_hypothesis_change=False,
    )


def test_materiality_policy_has_no_productive_authority() -> None:
    policy = _policy()

    assert policy.productive_authority is False
    assert len(policy.fingerprint()) == 64

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot authorize production",
    ):
        replace(policy, productive_authority=True)


def test_empirical_calibration_requires_evidence() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="requires calibration evidence",
    ):
        replace(
            _policy(),
            calibration_state=(
                SharedPolicyCalibrationState.EMPIRICALLY_CALIBRATED
            ),
        )


def test_materiality_detects_explicit_numeric_change() -> None:
    previous = _snapshot(snapshot_id="s1", observed_at=T0)
    current = _snapshot(
        snapshot_id="s2",
        observed_at=T0 + timedelta(minutes=1),
        confidence_bps=6800,
    )

    assessment = assess_snapshot_materiality(
        assessment_id="a1",
        previous=previous,
        current=current,
        policy=_policy(),
        assessed_at=current.observed_at,
    )

    assert assessment.disposition is SharedMaterialityDisposition.MATERIAL
    assert assessment.confidence_change_bps == 800
    assert assessment.emits_alert_authority is False


def test_subthreshold_change_is_not_material() -> None:
    previous = _snapshot(snapshot_id="s1", observed_at=T0)
    current = _snapshot(
        snapshot_id="s2",
        observed_at=T0 + timedelta(minutes=1),
        confidence_bps=6200,
    )

    assessment = assess_snapshot_materiality(
        assessment_id="a1",
        previous=previous,
        current=current,
        policy=_policy(),
        assessed_at=current.observed_at,
    )

    assert assessment.disposition is SharedMaterialityDisposition.NOT_MATERIAL
    assert "MATERIALITY_GATE_NOT_MET" in assessment.reason_codes


def test_required_world_state_change_is_binding() -> None:
    policy = replace(_policy(), require_world_state_change=True)
    previous = _snapshot(snapshot_id="s1", observed_at=T0)
    current = _snapshot(
        snapshot_id="s2",
        observed_at=T0 + timedelta(minutes=1),
        confidence_bps=6800,
    )

    assessment = assess_snapshot_materiality(
        assessment_id="a1",
        previous=previous,
        current=current,
        policy=policy,
        assessed_at=current.observed_at,
    )
    assert assessment.disposition is SharedMaterialityDisposition.NOT_MATERIAL

    changed = replace(current, snapshot_id="s3", world_state="TRANSITION")
    assessment2 = assess_snapshot_materiality(
        assessment_id="a2",
        previous=previous,
        current=changed,
        policy=policy,
        assessed_at=changed.observed_at,
    )
    assert assessment2.disposition is SharedMaterialityDisposition.MATERIAL


def test_unknown_or_insufficient_state_fails_to_insufficient() -> None:
    previous = _snapshot(snapshot_id="s1", observed_at=T0)
    current = _snapshot(
        snapshot_id="s2",
        observed_at=T0 + timedelta(minutes=1),
        confidence_bps=7000,
        epistemic_state=SharedEpistemicState.INSUFFICIENT,
    )

    assessment = assess_snapshot_materiality(
        assessment_id="a1",
        previous=previous,
        current=current,
        policy=_policy(),
        assessed_at=current.observed_at,
    )

    assert assessment.disposition is SharedMaterialityDisposition.INSUFFICIENT


def test_materiality_rejects_cross_instrument_and_horizon_comparison() -> None:
    previous = _snapshot(snapshot_id="s1", observed_at=T0)
    current = _snapshot(
        snapshot_id="s2",
        observed_at=T0 + timedelta(minutes=1),
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="identical canonical instrument",
    ):
        assess_snapshot_materiality(
            assessment_id="a1",
            previous=previous,
            current=replace(
                current,
                canonical_instrument_id="canonical:EURUSD",
            ),
            policy=_policy(),
            assessed_at=current.observed_at,
        )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="identical horizon",
    ):
        assess_snapshot_materiality(
            assessment_id="a2",
            previous=previous,
            current=replace(current, trader_horizon="H1"),
            policy=_policy(),
            assessed_at=current.observed_at,
        )


def test_materiality_rejects_future_snapshot() -> None:
    previous = _snapshot(snapshot_id="s1", observed_at=T0)
    current = _snapshot(
        snapshot_id="s2",
        observed_at=T0 + timedelta(minutes=1),
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot consume future snapshot",
    ):
        assess_snapshot_materiality(
            assessment_id="a1",
            previous=previous,
            current=current,
            policy=_policy(),
            assessed_at=T0 + timedelta(seconds=30),
        )


def test_opportunity_state_machine_forbids_resurrection_from_expired() -> None:
    assert (
        validate_opportunity_maturity_transition(
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.DEVELOPING,
        )
        is True
    )
    assert (
        validate_opportunity_maturity_transition(
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.EARLY,
        )
        is False
    )
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="illegal opportunity maturity transition",
    ):
        validate_opportunity_maturity_transition(
            SharedOpportunityMaturity.EXPIRED,
            SharedOpportunityMaturity.EARLY,
        )


def test_research_states_require_evidence_but_never_imply_orders() -> None:
    assert validate_regime_transition_state(
        SharedRegimeTransitionState.TRANSITION_DEVELOPING,
        evidence_refs=("fact:regime-change",),
    ) is SharedRegimeTransitionState.TRANSITION_DEVELOPING
    assert validate_continuation_support_state(
        SharedSupportState.STRONG,
        evidence_refs=("fact:continuation",),
    ) is SharedSupportState.STRONG
    assert validate_position_threat_state(
        SharedPositionThreatLevel.HIGH,
        evidence_refs=("fact:threat",),
    ) is SharedPositionThreatLevel.HIGH

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="position threat requires evidence",
    ):
        validate_position_threat_state(
            SharedPositionThreatLevel.HIGH,
            evidence_refs=(),
        )
