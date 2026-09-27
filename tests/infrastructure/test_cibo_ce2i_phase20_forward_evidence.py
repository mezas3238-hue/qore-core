from dataclasses import replace
from datetime import UTC, datetime, timedelta
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
    Phase20ForwardKnownOptionEvidence,
    Phase20ForwardOutcomeEvidence,
    Phase20PolicyCandidateLineage,
    assess_phase20d_forward_qualification,
    build_phase20_forward_decision_record,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_mpc import Phase20MpcKnownOption
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20AllocatorDisposition,
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

DECISION_AT = datetime(2026, 9, 27, 12, 30, tzinfo=UTC)


def _account() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="phase20d-forward-contract",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _lineage() -> Phase20PolicyCandidateLineage:
    return Phase20PolicyCandidateLineage(
        candidate_id="CIBO_PHASE20H20I_FORWARD_CANDIDATE_V1",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + "b" * 64,
        frozen_at=DECISION_AT - timedelta(days=1),
    )


def _candidate_evidence(
    *,
    provider_observed_at: datetime | None = None,
) -> Phase20ForwardCandidateEvidence:
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R43_GBPUSD,
        signal_fingerprint="phase20d-signal-1",
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
        observed_at=(
            provider_observed_at
            if provider_observed_at is not None
            else DECISION_AT - timedelta(seconds=1)
        ),
    )
    expectation = CausalOpportunityExpectation(
        evidence_id="phase20d-expectation-1",
        as_of=DECISION_AT - timedelta(seconds=2),
        basis=CausalExpectationBasis.CURRENT_STATE_FORECAST,
        expected_net_value_usd=Decimal("5"),
        expected_capital_minutes=Decimal("10"),
    )
    candidate = CapitalOpportunityCandidate(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        provider_symbol=opportunity.provider_symbol,
        decision_as_of=DECISION_AT,
        expectation=expectation,
        stop_risk_usd=Decimal("11"),
        margin_usd=Decimal("10"),
        concentration_group="GBPUSD",
        concentration_risk_usd=Decimal("11"),
    )
    return Phase20ForwardCandidateEvidence(
        provider_evidence_id="provider-snapshot-1",
        opportunity=opportunity,
        provider_observation=provider,
        candidate=candidate,
    )


def _known_option(
    *,
    known_as_of: datetime | None = None,
) -> Phase20ForwardKnownOptionEvidence:
    return Phase20ForwardKnownOptionEvidence(
        evidence_id="known-option-1",
        option=Phase20MpcKnownOption(
            opportunity_id="future-option-1",
            decision_step=1,
            minimum_stop_risk_usd=Decimal("5"),
            minimum_margin_usd=Decimal("10"),
        ),
        known_as_of=(
            known_as_of
            if known_as_of is not None
            else DECISION_AT - timedelta(seconds=5)
        ),
        active_at_decision=True,
        expires_at=DECISION_AT + timedelta(hours=1),
    )


def _decision(
    *,
    kind: Phase20ForwardEvidenceKind = (
        Phase20ForwardEvidenceKind.SYNTHETIC_CONTRACT
    ),
    known_options: tuple[Phase20ForwardKnownOptionEvidence, ...] | None = None,
) -> Phase20ForwardDecisionEvidence:
    account = _account()
    return Phase20ForwardDecisionEvidence(
        evidence_id="phase20d-decision-1",
        evidence_kind=kind,
        decision_at=DECISION_AT,
        lineage=_lineage(),
        account_identity=account,
        mission=derive_cibo_capital_mission(account),
        capital_snapshot_id="capital-generation-7",
        risk_snapshot_id="risk-generation-11",
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
        horizon_steps=2,
        candidates=(_candidate_evidence(),),
        known_options=(
            (_known_option(),)
            if known_options is None
            else known_options
        ),
    )


def test_phase20d_seals_single_candidate_20h_and_20i_inputs() -> None:
    evidence = _decision()
    record = build_phase20_forward_decision_record(evidence)

    assert record.evidence_sha256 == phase20_forward_evidence_sha256(evidence)
    assert record.mpc_plan.considered_option_ids == ("future-option-1",)
    assert record.mpc_plan.reserve_stop_risk_usd == Decimal("5")
    assert (
        record.allocator_decision.disposition
        is Phase20AllocatorDisposition.ALLOCATE
    )
    assert record.allocator_decision.allocation is not None
    assert record.allocator_decision.allocation.selected_signal_fingerprints == (
        "phase20d-signal-1",
    )
    assert record.allocator_decision.applied_tools == ("T15",)
    assert record.phase20d_qualified is False


def test_phase20d_synthetic_contract_cannot_qualify_as_fresh_forward() -> None:
    decision = _decision()
    outcome = Phase20ForwardOutcomeEvidence(
        evidence_id="outcome-1",
        decision_evidence_sha256=phase20_forward_evidence_sha256(decision),
        signal_fingerprint="phase20d-signal-1",
        observed_at=DECISION_AT + timedelta(hours=2),
        realized_structural_outcome_r=Decimal("1.5"),
        outcome_reconciled=True,
    )

    result = assess_phase20d_forward_qualification(
        decision=decision,
        outcome=outcome,
    )

    assert result.eligible is False
    assert result.reasons == ("DECISION_NOT_FORWARD_OBSERVED",)


def test_phase20d_forward_observed_pair_is_eligible_when_causally_bound() -> None:
    decision = _decision(kind=Phase20ForwardEvidenceKind.FORWARD_OBSERVED)
    outcome = Phase20ForwardOutcomeEvidence(
        evidence_id="outcome-forward-1",
        decision_evidence_sha256=phase20_forward_evidence_sha256(decision),
        signal_fingerprint="phase20d-signal-1",
        observed_at=DECISION_AT + timedelta(hours=2),
        realized_structural_outcome_r=Decimal("-1"),
        outcome_reconciled=True,
    )

    result = assess_phase20d_forward_qualification(
        decision=decision,
        outcome=outcome,
    )

    assert result.eligible is True
    assert result.reasons == ()


def test_phase20d_rejects_provider_snapshot_from_after_decision() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="provider observation cannot postdate capital decision",
    ):
        _candidate_evidence(
            provider_observed_at=DECISION_AT + timedelta(seconds=1)
        )


def test_phase20d_rejects_option_discovered_after_decision() -> None:
    future_option = _known_option(
        known_as_of=DECISION_AT + timedelta(seconds=1)
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="known option cannot be discovered after decision",
    ):
        _decision(known_options=(future_option,))


def test_phase20d_digest_is_deterministic_and_materially_sensitive() -> None:
    left = _decision()
    right = _decision()
    assert phase20_forward_evidence_sha256(left) == (
        phase20_forward_evidence_sha256(right)
    )

    changed = replace(left, capital_snapshot_id="capital-generation-8")
    assert phase20_forward_evidence_sha256(left) != (
        phase20_forward_evidence_sha256(changed)
    )


def test_phase20d_outcome_must_bind_exact_decision_digest() -> None:
    decision = _decision(kind=Phase20ForwardEvidenceKind.FORWARD_OBSERVED)
    outcome = Phase20ForwardOutcomeEvidence(
        evidence_id="outcome-bad-digest",
        decision_evidence_sha256="sha256:" + "c" * 64,
        signal_fingerprint="phase20d-signal-1",
        observed_at=DECISION_AT + timedelta(hours=2),
        realized_structural_outcome_r=Decimal("1"),
        outcome_reconciled=True,
    )

    result = assess_phase20d_forward_qualification(
        decision=decision,
        outcome=outcome,
    )

    assert result.eligible is False
    assert "OUTCOME_DECISION_DIGEST_MISMATCH" in result.reasons
