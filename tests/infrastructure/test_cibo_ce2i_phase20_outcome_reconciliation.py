from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

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
    Phase20ForwardPopulationDisposition,
    Phase20ForwardPopulationSlotEvidence,
    Phase20PolicyCandidateLineage,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
    append_reconciled_phase20_forward_outcome,
    reconcile_phase20_forward_outcome,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

DECISION_AT = datetime(2026, 9, 27, 17, 0, tzinfo=UTC)


def _decision(
    *,
    kind: Phase20ForwardEvidenceKind = Phase20ForwardEvidenceKind.FORWARD_OBSERVED,
) -> Phase20ForwardDecisionEvidence:
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="outcome-vt31",
        qore_symbol="NAS100",
        provider_symbol="NAS100",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
    )
    provider = ProviderEconomicObservation(
        provider_key="ctrader",
        qore_symbol="NAS100",
        provider_symbol="NAS100",
        bid=Decimal("100"),
        ask=Decimal("100"),
        contract_size=Decimal("1"),
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
    expectation = CausalOpportunityExpectation(
        evidence_id="frozen-prior",
        as_of=DECISION_AT - timedelta(seconds=1),
        basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
        expected_net_value_usd=Decimal("2"),
        expected_capital_minutes=Decimal("6"),
    )
    candidate = CapitalOpportunityCandidate(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        provider_symbol=opportunity.provider_symbol,
        decision_as_of=DECISION_AT,
        expectation=expectation,
        stop_risk_usd=Decimal("10"),
        margin_usd=Decimal("10"),
        concentration_group="INDEX",
        concentration_risk_usd=Decimal("10"),
    )
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    account = CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="demo-forward",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    return Phase20ForwardDecisionEvidence(
        evidence_id="outcome-decision",
        decision_epoch_id="outcome-epoch",
        evidence_kind=kind,
        decision_at=DECISION_AT,
        lineage=Phase20PolicyCandidateLineage(
            candidate_id=frozen.candidate_id,
            code_sha=frozen.code_sha,
            parameter_sha256=frozen.parameter_sha256(),
            frozen_at=frozen.frozen_at,
        ),
        account_identity=account,
        mission=derive_cibo_capital_mission(account),
        capital_snapshot_id="capital-1",
        capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        risk_snapshot_id="risk-1",
        risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("INDEX", Decimal("100")),),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.1"),
            margin_utilization=Decimal("0.1"),
            drawdown_utilization=Decimal("0.1"),
            opportunity_count=1,
        ),
        current_step=0,
        horizon_steps=frozen.mpc_horizon_steps,
        population_slots=(
            Phase20ForwardPopulationSlotEvidence(
                slot_id="VT31_NAS100|NAS100",
                trader_id=TraderLineage.VT31_NAS100,
                qore_symbol="NAS100",
                observed_at=DECISION_AT - timedelta(milliseconds=1),
                disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
                reason="VALID_TRADER_OPPORTUNITY",
                signal_fingerprint="outcome-vt31",
            ),
        ),
        candidates=(
            Phase20ForwardCandidateEvidence(
                provider_evidence_id="provider-outcome",
                opportunity=opportunity,
                provider_observation=provider,
                candidate=candidate,
            ),
        ),
    )


def _settlement(*, closed: bool = True) -> CmaSettlementState:
    state = CmaSettlementState(
        signal_fingerprint="outcome-vt31",
        position_id=77,
    )
    state = apply_settlement(
        state,
        CmaSettlementRecord(
            event="CTRADER_DEMO_PARTIAL_SETTLEMENT",
            deal_id=1001,
            signal_fingerprint="outcome-vt31",
            position_id=77,
            net_profit_usd=Decimal("5"),
            position_open_after=True,
        ),
    )
    if closed:
        state = apply_settlement(
            state,
            CmaSettlementRecord(
                event="CTRADER_DEMO_EXIT_SETTLEMENT",
                deal_id=1002,
                signal_fingerprint="outcome-vt31",
                position_id=77,
                net_profit_usd=Decimal("15"),
                position_open_after=False,
            ),
        )
    return state


def _risk(decision: Phase20ForwardDecisionEvidence) -> Phase20ExecutedRiskEvidence:
    return Phase20ExecutedRiskEvidence(
        evidence_id="executed-risk-77",
        decision_evidence_sha256=phase20_forward_evidence_sha256(decision),
        signal_fingerprint="outcome-vt31",
        position_id=77,
        executed_initial_stop_risk_usd=Decimal("10"),
        observed_at=DECISION_AT + timedelta(seconds=1),
        fill_evidence_refs=("fill-1",),
        fill_reconciled=True,
        mutation_outcome_known=True,
    )


def test_reconciled_terminal_outcome_uses_executed_risk_denominator() -> None:
    decision = _decision()

    outcome = reconcile_phase20_forward_outcome(
        decision=decision,
        settlement=_settlement(),
        executed_risk=_risk(decision),
        reconciled_at=DECISION_AT + timedelta(hours=1),
    )

    assert outcome.outcome_reconciled is True
    assert outcome.realized_structural_outcome_r == Decimal("2")
    assert outcome.signal_fingerprint == "outcome-vt31"


def test_outcome_reconciliation_rejects_partial_open_settlement() -> None:
    decision = _decision()

    with pytest.raises(
        CiboCapitalManagementError,
        match="terminal closed settlement",
    ):
        reconcile_phase20_forward_outcome(
            decision=decision,
            settlement=_settlement(closed=False),
            executed_risk=_risk(decision),
            reconciled_at=DECISION_AT + timedelta(hours=1),
        )


def test_outcome_reconciliation_rejects_unreconciled_risk_evidence() -> None:
    decision = _decision()

    with pytest.raises(
        CiboCapitalManagementError,
        match="must be fully reconciled",
    ):
        Phase20ExecutedRiskEvidence(
            evidence_id="bad-risk",
            decision_evidence_sha256=phase20_forward_evidence_sha256(decision),
            signal_fingerprint="outcome-vt31",
            position_id=77,
            executed_initial_stop_risk_usd=Decimal("10"),
            observed_at=DECISION_AT + timedelta(seconds=1),
            fill_evidence_refs=("fill-1",),
            fill_reconciled=False,
            mutation_outcome_known=True,
        )


def test_outcome_reconciliation_rejects_synthetic_decision() -> None:
    decision = _decision(kind=Phase20ForwardEvidenceKind.SYNTHETIC_CONTRACT)

    with pytest.raises(
        CiboCapitalManagementError,
        match="FORWARD_OBSERVED",
    ):
        reconcile_phase20_forward_outcome(
            decision=decision,
            settlement=_settlement(),
            executed_risk=_risk(decision),
            reconciled_at=DECISION_AT + timedelta(hours=1),
        )


def test_append_reconciled_outcome_is_restart_safe_and_idempotent(
    tmp_path: Path,
) -> None:
    decision = _decision()
    store = DurablePhase20ForwardEvidenceStore(tmp_path / "forward.json")
    first = store.seal_decision(decision, expected_generation=0)

    second = append_reconciled_phase20_forward_outcome(
        store=store,
        decision=decision,
        settlement=_settlement(),
        executed_risk=_risk(decision),
        reconciled_at=DECISION_AT + timedelta(hours=1),
    )
    third = append_reconciled_phase20_forward_outcome(
        store=store,
        decision=decision,
        settlement=_settlement(),
        executed_risk=_risk(decision),
        reconciled_at=DECISION_AT + timedelta(hours=1),
    )

    assert first.generation == 1
    assert second.generation == 2
    assert third.generation == 2
    restarted = DurablePhase20ForwardEvidenceStore(
        tmp_path / "forward.json"
    ).load()
    assert restarted == third
    assert len(restarted.outcomes) == 1
