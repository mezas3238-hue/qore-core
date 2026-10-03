from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    CiboRiskRequest,
    ReservationState,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    plan_minimal_seed,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 3, 0, tzinfo=UTC)


@dataclass(slots=True)
class _ProviderBudget:
    provider_headroom: Decimal = Decimal("100")
    max_risk_at_any_time: Decimal = Decimal("100")
    active_mll: Decimal = Decimal("50")
    hard_breach: bool = False


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _opportunity(candidate: TraderLabCandidateBinding) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint=_tag(candidate, "signal"),
        qore_symbol="BTCUSD",
        provider_symbol="BTCUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("1"),
        margin_per_volume=Decimal("1"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("1"),
        decision_context=(
            ("trader_lab_candidate", candidate.fingerprint.value),
        ),
    )


def _capital() -> CiboCapitalState:
    return CiboCapitalState(
        assigned_capital_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("20"),
        base_capital_at_risk_usd=Decimal("0"),
        realized_net_profit_usd=Decimal("0"),
        protected_open_economic_floor_usd=Decimal("0"),
        proven_self_financing_capacity_usd=Decimal("0"),
        reserved_expansion_risk_usd=Decimal("0"),
        cost_reserve_usd=Decimal("0"),
    )


def _snapshot(
    candidate: TraderLabCandidateBinding,
    *,
    headroom: Decimal = Decimal("20"),
) -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        account_binding_id=_tag(candidate, "account"),
        equity=Decimal("100"),
        margin_used=Decimal("0"),
        free_margin=Decimal("100"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=headroom,
        provider_budget=_ProviderBudget(
            provider_headroom=headroom,
            max_risk_at_any_time=headroom,
        ),
        reconciled_at=NOW,
    )


def _request(
    candidate: TraderLabCandidateBinding,
    opportunity: TraderOpportunityEnvelope,
    *,
    requested_volume: Decimal,
) -> CiboRiskRequest:
    return CiboRiskRequest(
        request_id=_tag(candidate, "risk-request"),
        trader_id=opportunity.trader_id,
        signal_fingerprint=opportunity.signal_fingerprint,
        qore_symbol=opportunity.qore_symbol,
        provider_symbol=opportunity.provider_symbol,
        side=opportunity.side,
        entry_type=opportunity.entry_type,
        intended_entry=opportunity.intended_entry,
        stop_loss=opportunity.stop_loss,
        take_profit=opportunity.take_profit,
        requested_volume=requested_volume,
        volume_step=opportunity.volume_step,
        minimum_volume=opportunity.minimum_volume,
        stop_loss_per_volume=opportunity.stop_loss_per_volume,
        margin_per_volume=opportunity.margin_per_volume,
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        strategy_requested_risk_usd=None,
    )


def test_trader_lab_cma_risk_and_settlement_full_chain(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=930)
    opportunity = _opportunity(candidate)

    plan = plan_minimal_seed(opportunity, _capital())
    assert plan.action is CapitalAction.OPEN_MINIMAL_SEED
    assert plan.volume == Decimal("0.01")

    risk = AccountWideRiskEngine()
    authorization = risk.authorize(
        _request(
            candidate,
            opportunity,
            requested_volume=plan.volume,
        ),
        _snapshot(candidate),
        now=NOW,
    )
    assert authorization.decision is RiskDecision.ALLOW
    assert authorization.authorized_volume == plan.volume
    assert authorization.monetary_stop_loss == plan.stop_risk_usd

    risk.record_full_fill(authorization.authorization_id)
    reservation = risk.reservation_for(authorization.authorization_id)
    assert reservation is not None
    assert reservation.state is ReservationState.FILLED_UNRECONCILED

    risk.reconcile_fill(authorization.authorization_id)
    reservation = risk.reservation_for(authorization.authorization_id)
    assert reservation is not None
    assert reservation.state is ReservationState.RELEASED
    assert risk.active_reserved_stop_risk() == 0

    signal = opportunity.signal_fingerprint
    state = CmaSettlementState(
        signal_fingerprint=signal,
        position_id=93001,
    )
    state = apply_settlement(
        state,
        CmaSettlementRecord(
            event="CTRADER_DEMO_ENTRY_COST_SETTLEMENT",
            deal_id=93010,
            signal_fingerprint=signal,
            position_id=93001,
            net_profit_usd=Decimal("-0.10"),
            position_open_after=True,
        ),
    )
    state = apply_settlement(
        state,
        CmaSettlementRecord(
            event="CTRADER_DEMO_PARTIAL_SETTLEMENT",
            deal_id=93011,
            signal_fingerprint=signal,
            position_id=93001,
            net_profit_usd=Decimal("0.40"),
            position_open_after=True,
        ),
    )
    state = apply_settlement(
        state,
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=93012,
            signal_fingerprint=signal,
            position_id=93001,
            net_profit_usd=Decimal("0.70"),
            position_open_after=False,
        ),
    )
    assert state.position_closed is True
    assert state.realized_net_pnl_usd == Decimal("1.00")


def test_trader_lab_qore_risk_fails_closed_when_minimum_cannot_fit(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=931)
    opportunity = _opportunity(candidate)
    risk = AccountWideRiskEngine()

    authorization = risk.authorize(
        _request(
            candidate,
            opportunity,
            requested_volume=Decimal("0.01"),
        ),
        _snapshot(candidate, headroom=Decimal("0.005")),
        now=NOW,
    )

    assert authorization.decision is RiskDecision.REJECT
    assert authorization.authorized_volume == 0
    assert authorization.monetary_stop_loss == 0
    assert risk.active_reserved_stop_risk() == 0
