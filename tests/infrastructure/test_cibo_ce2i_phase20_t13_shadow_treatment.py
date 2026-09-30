from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_evidence import (
    build_missing_advanced_evidence_snapshot,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardCandidateEvidence,
    Phase20ForwardDecisionEvidence,
    Phase20ForwardEvidenceKind,
    Phase20ForwardPopulationDisposition,
    Phase20ForwardPopulationSlotEvidence,
    Phase20PolicyCandidateLineage,
    build_phase20_forward_decision_record,
    phase20_forward_decision_record_json,
    phase20_forward_decision_record_sha256,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
    Phase20T13ShadowRecommendation,
    t13_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment import (
    build_phase20_t13_shadow_treatment,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

DECISION_AT = T13_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=5)


def _evidence() -> Phase20ForwardDecisionEvidence:
    account = CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="t13-shadow-treatment",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R43_GBPUSD,
        signal_fingerprint="t13-signal",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("11"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
    )
    provider = ProviderEconomicObservation(
        provider_key="ctrader-demo",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        bid=Decimal("100"),
        ask=Decimal("100.1"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
        volume_step=Decimal("1"),
        margin_per_volume=Decimal("10"),
        commission_per_volume_usd=Decimal("0"),
        slippage_reserve_per_volume_usd=Decimal("0"),
        observed_at=DECISION_AT - timedelta(seconds=1),
    )
    candidate = CapitalOpportunityCandidate(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        provider_symbol=opportunity.provider_symbol,
        decision_as_of=DECISION_AT,
        expectation=CausalOpportunityExpectation(
            evidence_id="t13-expectation",
            as_of=DECISION_AT - timedelta(hours=1),
            basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
            expected_net_value_usd=Decimal("5"),
            expected_capital_minutes=Decimal("10"),
        ),
        stop_risk_usd=Decimal("11"),
        margin_usd=Decimal("10"),
        concentration_group="GBPUSD",
        concentration_risk_usd=Decimal("11"),
    )
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    lineage = Phase20PolicyCandidateLineage(
        candidate_id=frozen.candidate_id,
        code_sha=frozen.code_sha,
        parameter_sha256=frozen.parameter_sha256(),
        frozen_at=frozen.frozen_at,
    )
    return Phase20ForwardDecisionEvidence(
        evidence_id="t13-evidence",
        decision_epoch_id="t13-epoch",
        evidence_kind=Phase20ForwardEvidenceKind.FORWARD_OBSERVED,
        decision_at=DECISION_AT,
        lineage=lineage,
        account_identity=account,
        mission=derive_cibo_capital_mission(account),
        capital_snapshot_id="capital-1",
        capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        risk_snapshot_id="risk-1",
        risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("GBPUSD", Decimal("20")),),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.20"),
            margin_utilization=Decimal("0.20"),
            drawdown_utilization=Decimal("0.10"),
            opportunity_count=1,
        ),
        current_step=0,
        horizon_steps=frozen.mpc_horizon_steps,
        population_slots=(
            Phase20ForwardPopulationSlotEvidence(
                slot_id="R43_GBPUSD|GBPUSD|t13-epoch",
                trader_id=TraderLineage.R43_GBPUSD,
                qore_symbol="GBPUSD",
                observed_at=DECISION_AT - timedelta(milliseconds=1),
                disposition=(
                    Phase20ForwardPopulationDisposition.CANDIDATE
                ),
                reason="fresh T13 shadow treatment fixture",
                signal_fingerprint="t13-signal",
            ),
        ),
        candidates=(
            Phase20ForwardCandidateEvidence(
                provider_evidence_id="provider-1",
                opportunity=opportunity,
                provider_observation=provider,
                candidate=candidate,
            ),
        ),
        known_options=(),
        advanced_evidence_snapshot=(
            build_missing_advanced_evidence_snapshot(
                decision_at=DECISION_AT,
            )
        ),
    )


def _baseline_policy(
    evidence: Phase20ForwardDecisionEvidence,
) -> Phase20ForwardPolicyDecisionSeal:
    record = build_phase20_forward_decision_record(evidence)
    allocation = record.allocator_decision.allocation
    selected = (
        ()
        if allocation is None
        else allocation.selected_signal_fingerprints
    )
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=record.evidence_sha256,
        policy_record_sha256=(
            phase20_forward_decision_record_sha256(record)
        ),
        allocator_disposition=record.allocator_decision.disposition.value,
        selected_signal_fingerprints=selected,
        canonical_record_json=phase20_forward_decision_record_json(record),
    )


def _recommendation(
    evidence: Phase20ForwardDecisionEvidence,
    *,
    reserve: Decimal,
) -> Phase20T13ShadowRecommendation:
    return Phase20T13ShadowRecommendation(
        policy_id="CIBO_T13_ONE_MINIMUM_SEED_RESERVE_SHADOW_V1",
        policy_sha256=t13_shadow_policy_sha256(),
        decision_epoch_id=evidence.decision_epoch_id,
        decision_evidence_sha256=phase20_forward_evidence_sha256(evidence),
        decision_at=evidence.decision_at,
        causal_pressure_active=reserve > 0,
        arrival_evidence_available=reserve > 0,
        reserve_triggered=reserve > 0,
        reserved_risk_usd=reserve,
        minimum_seed_risk_usd=Decimal("10"),
        hard_risk_headroom_usd=evidence.hard_risk_headroom_usd,
        full_seed_preserved=reserve > 0,
        source_decision_sha256s=(
            ("sha256:" + ("1" * 64),) if reserve > 0 else ()
        ),
        source_outcome_evidence_ids=(
            ("prior-outcome",) if reserve > 0 else ()
        ),
    )


def test_t13_shadow_treatment_changes_only_risk_headroom() -> None:
    evidence = _evidence()
    baseline = _baseline_policy(evidence)
    treatment = build_phase20_t13_shadow_treatment(
        evidence=evidence,
        baseline_policy=baseline,
        recommendation=_recommendation(
            evidence,
            reserve=Decimal("10"),
        ),
    )

    assert treatment.baseline_allocator_input_stop_risk_usd == Decimal("20")
    assert treatment.treatment_allocator_input_stop_risk_usd == Decimal("10")
    assert treatment.allocator_input_margin_usd == Decimal("100")
    assert treatment.baseline_selected_signal_fingerprints == ("t13-signal",)
    assert treatment.treatment_selected_signal_fingerprints == ()
    assert treatment.baseline_only_signal_fingerprints == ("t13-signal",)
    assert treatment.treatment_only_signal_fingerprints == ()
    assert treatment.selection_changed is True
    assert treatment.outcome_aware is False
    assert treatment.runtime_authority is False


def test_t13_zero_reserve_reproduces_sealed_baseline() -> None:
    evidence = _evidence()
    baseline = _baseline_policy(evidence)
    treatment = build_phase20_t13_shadow_treatment(
        evidence=evidence,
        baseline_policy=baseline,
        recommendation=_recommendation(
            evidence,
            reserve=Decimal("0"),
        ),
    )

    assert treatment.treatment_allocator_input_stop_risk_usd == Decimal("20")
    assert treatment.treatment_selected_signal_fingerprints == (
        treatment.baseline_selected_signal_fingerprints
    )
    assert treatment.selection_changed is False


def test_t13_shadow_treatment_rejects_baseline_policy_digest_drift() -> None:
    evidence = _evidence()
    baseline = _baseline_policy(evidence)
    drifted = Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=baseline.evidence_sha256,
        policy_record_sha256="sha256:" + ("f" * 64),
        allocator_disposition=baseline.allocator_disposition,
        selected_signal_fingerprints=baseline.selected_signal_fingerprints,
        canonical_record_json=baseline.canonical_record_json,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot be reproduced exactly",
    ):
        build_phase20_t13_shadow_treatment(
            evidence=evidence,
            baseline_policy=drifted,
            recommendation=_recommendation(
                evidence,
                reserve=Decimal("10"),
            ),
        )


def test_t13_shadow_treatment_rejects_wrong_evidence_binding() -> None:
    evidence = _evidence()
    baseline = _baseline_policy(evidence)
    recommendation = _recommendation(
        evidence,
        reserve=Decimal("10"),
    )
    wrong = Phase20T13ShadowRecommendation(
        policy_id=recommendation.policy_id,
        policy_sha256=recommendation.policy_sha256,
        decision_epoch_id=recommendation.decision_epoch_id,
        decision_evidence_sha256="sha256:" + ("e" * 64),
        decision_at=recommendation.decision_at,
        causal_pressure_active=recommendation.causal_pressure_active,
        arrival_evidence_available=(
            recommendation.arrival_evidence_available
        ),
        reserve_triggered=recommendation.reserve_triggered,
        reserved_risk_usd=recommendation.reserved_risk_usd,
        minimum_seed_risk_usd=recommendation.minimum_seed_risk_usd,
        hard_risk_headroom_usd=recommendation.hard_risk_headroom_usd,
        full_seed_preserved=recommendation.full_seed_preserved,
        source_decision_sha256s=recommendation.source_decision_sha256s,
        source_outcome_evidence_ids=(
            recommendation.source_outcome_evidence_ids
        ),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="evidence binding mismatch",
    ):
        build_phase20_t13_shadow_treatment(
            evidence=evidence,
            baseline_policy=baseline,
            recommendation=wrong,
        )
