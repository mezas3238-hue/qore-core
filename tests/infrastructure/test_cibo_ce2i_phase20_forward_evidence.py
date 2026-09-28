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
    Phase20ForwardPopulationDisposition,
    Phase20ForwardPopulationSlotEvidence,
    Phase20PolicyCandidateLineage,
    assess_phase20d_forward_qualification,
    build_phase20_forward_decision_record,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_mpc import Phase20MpcKnownOption
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
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

DECISION_AT = datetime(2026, 9, 28, 4, 35, tzinfo=UTC)


def _account() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="phase20d-forward-contract",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _lineage() -> Phase20PolicyCandidateLineage:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    return Phase20PolicyCandidateLineage(
        candidate_id=candidate.candidate_id,
        code_sha=candidate.code_sha,
        parameter_sha256=candidate.parameter_sha256(),
        frozen_at=candidate.frozen_at,
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
        decision_epoch_id="phase20d-epoch-1",
        evidence_kind=kind,
        decision_at=DECISION_AT,
        lineage=_lineage(),
        account_identity=account,
        mission=derive_cibo_capital_mission(account),
        capital_snapshot_id="capital-generation-7",
        capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        risk_snapshot_id="risk-generation-11",
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
        horizon_steps=2,
        population_slots=(
            Phase20ForwardPopulationSlotEvidence(
                slot_id="R43_GBPUSD|GBPUSD|phase20d-epoch-1",
                trader_id=TraderLineage.R43_GBPUSD,
                qore_symbol="GBPUSD",
                observed_at=DECISION_AT - timedelta(milliseconds=1),
                disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
                reason="synthetic candidate fixture",
                signal_fingerprint="phase20d-signal-1",
            ),
        ),
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
    assert record.allocator_input_stop_risk_headroom_usd == Decimal("15")
    assert record.allocator_input_margin_headroom_usd == Decimal("90")
    assert record.mpc_reserve_applied_before_allocator is True
    assert (
        record.allocator_decision.disposition
        is Phase20AllocatorDisposition.ALLOCATE
    )
    assert record.allocator_decision.allocation is not None
    assert record.allocator_decision.allocation.selected_signal_fingerprints == (
        "phase20d-signal-1",
    )
    assert record.allocator_decision.applied_tools == ("T15",)
    assert record.allocator_decision.reserve_stop_risk_usd == 0
    assert record.phase20d_qualified is False
    assert record.full_surface.complete_registry is True
    assert record.full_surface.registry_codes == tuple(
        f"T{index:02d}" for index in range(1, 21)
    )
    assert tuple(
        item.tool_code for item in record.full_surface.advanced_decisions
    ) == ("T02", "T03", "T04", "T17", "T08", "T10", "T16")


def test_phase20d_mpc_reserve_prevents_allocator_capacity_overcommit() -> None:
    base_candidate = _candidate_evidence()
    high_risk_candidate = replace(
        base_candidate.candidate,
        stop_risk_usd=Decimal("20"),
        concentration_risk_usd=Decimal("20"),
    )
    sealed_candidate = replace(
        base_candidate,
        candidate=high_risk_candidate,
    )
    decision = replace(
        _decision(),
        candidates=(sealed_candidate,),
    )

    record = build_phase20_forward_decision_record(decision)

    assert record.mpc_plan.reserve_stop_risk_usd == Decimal("5")
    assert record.allocator_input_stop_risk_headroom_usd == Decimal("15")
    assert (
        record.allocator_decision.disposition
        is Phase20AllocatorDisposition.NO_ELIGIBLE_ALLOCATION
    )
    assert record.allocator_decision.allocation is not None
    assert record.allocator_decision.allocation.selected_signal_fingerprints == ()
    assert record.allocator_decision.allocation.used_stop_risk_usd == 0
    assert record.allocator_decision.allocation.used_margin_usd == 0


def test_phase20d_rejects_stale_capital_snapshot() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="capital snapshot exceeds frozen freshness bound",
    ):
        replace(
            _decision(),
            capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=3),
        )


def test_phase20d_rejects_stale_risk_snapshot() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="Risk snapshot exceeds frozen freshness bound",
    ):
        replace(
            _decision(),
            risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=3),
        )


def test_phase20d_rejects_stale_provider_snapshot() -> None:
    stale = _candidate_evidence(
        provider_observed_at=DECISION_AT - timedelta(seconds=3)
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="provider snapshot exceeds frozen freshness bound",
    ):
        replace(_decision(), candidates=(stale,))


def test_phase20d_rejects_stale_current_state_expectation() -> None:
    base = _candidate_evidence()
    stale_expectation = replace(
        base.candidate.expectation,
        as_of=DECISION_AT - timedelta(seconds=3),
    )
    stale_candidate = replace(
        base.candidate,
        expectation=stale_expectation,
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="current causal expectation exceeds frozen freshness bound",
    ):
        replace(
            _decision(),
            candidates=(replace(base, candidate=stale_candidate),),
        )


def test_phase20d_rejects_lineage_drift() -> None:
    wrong = replace(_lineage(), code_sha="c" * 40)
    with pytest.raises(
        CiboCapitalManagementError,
        match="lineage does not match frozen policy candidate",
    ):
        replace(_decision(), lineage=wrong)


def test_phase20d_rejects_mpc_horizon_drift() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="horizon_steps drift from frozen policy candidate",
    ):
        replace(_decision(), horizon_steps=3)


def test_phase20d_synthetic_contract_cannot_qualify_as_fresh_forward() -> None:
    decision = _decision()
    outcome = Phase20ForwardOutcomeEvidence(
        evidence_id="outcome-1",
        decision_evidence_sha256=phase20_forward_evidence_sha256(decision),
        signal_fingerprint="phase20d-signal-1",
        position_id=1,
        execution_risk_evidence_id="risk-evidence-1",
        settlement_deal_ids=(1,),
        fill_evidence_refs=("fill-1",),
        observed_at=DECISION_AT + timedelta(hours=2),
        realized_net_pnl_usd=Decimal("15"),
        executed_initial_stop_risk_usd=Decimal("10"),
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
        position_id=2,
        execution_risk_evidence_id="risk-evidence-2",
        settlement_deal_ids=(2,),
        fill_evidence_refs=("fill-2",),
        observed_at=DECISION_AT + timedelta(hours=2),
        realized_net_pnl_usd=Decimal("-10"),
        executed_initial_stop_risk_usd=Decimal("10"),
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
        position_id=3,
        execution_risk_evidence_id="risk-evidence-3",
        settlement_deal_ids=(3,),
        fill_evidence_refs=("fill-3",),
        observed_at=DECISION_AT + timedelta(hours=2),
        realized_net_pnl_usd=Decimal("10"),
        executed_initial_stop_risk_usd=Decimal("10"),
        realized_structural_outcome_r=Decimal("1"),
        outcome_reconciled=True,
    )

    result = assess_phase20d_forward_qualification(
        decision=decision,
        outcome=outcome,
    )

    assert result.eligible is False
    assert "OUTCOME_DECISION_DIGEST_MISMATCH" in result.reasons

def test_phase20d_rejects_population_manifest_candidate_mismatch() -> None:
    decision = _decision()
    slot = decision.population_slots[0]
    with pytest.raises(
        CiboCapitalManagementError,
        match="population manifest must exactly match candidates",
    ):
        replace(
            decision,
            population_slots=(
                replace(slot, signal_fingerprint="different-signal"),
            ),
        )


def test_phase20d_population_manifest_can_retain_non_candidate_slots() -> None:
    decision = _decision()
    abstain = Phase20ForwardPopulationSlotEvidence(
        slot_id="R34_XAUUSD|XAUUSD|phase20d-epoch-1",
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        observed_at=DECISION_AT - timedelta(milliseconds=1),
        disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
        reason="NO_SETUP",
    )

    expanded = replace(
        decision,
        population_slots=decision.population_slots + (abstain,),
    )

    assert len(expanded.population_slots) == 2
    assert expanded.population_slots[1].signal_fingerprint is None

