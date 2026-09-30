"""GEN-C6/T19 deployment and settlement orchestration for the compound cycle.

This module applies an already-frozen GEN-C6 shadow decision to research-only
compound ledgers. It never creates a new allocation policy and grants no
runtime, Risk, execution, LIVE or real-capital authority.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationReservation,
    PortfolioAllocationReservationState,
)
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementState
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    CiboCompoundCycleState,
    CompoundCycleDeployment,
    CompoundCycleMarketRecord,
    CompoundCycleSettlementRecord,
    profit_evidence_from_settlement,
    require_event_order,
    require_new_settlement,
    require_terminal_settlement,
    settlement_sha256,
)
from qore.infrastructure.cibo_internal_capital_market import (
    CapitalScarcityEvent,
    Genc6Action,
    Genc6InternalCapitalMarketDecision,
    Genc6MarginalCapitalCandidate,
    build_genc6_portfolio_state,
    evaluate_genc6_internal_capital_market_shadow,
    genc6_portfolio_state_sha256,
)


def apply_internal_capital_market_decision(
    state: CiboCompoundCycleState,
    *,
    event_id: str,
    scarcity_event: CapitalScarcityEvent,
    decision: Genc6InternalCapitalMarketDecision,
    source_lot_id: str | None = None,
) -> CiboCompoundCycleState:
    """Bind exact current portfolio state, then apply the frozen GEN-C6 action."""

    require_event_order(state, event_id, decision.decision_at)
    if not isinstance(scarcity_event, CapitalScarcityEvent):
        raise CiboCompoundCapitalError(
            "compound cycle requires canonical scarcity event"
        )
    if not isinstance(decision, Genc6InternalCapitalMarketDecision):
        raise CiboCompoundCapitalError(
            "compound cycle requires canonical GEN-C6 decision"
        )
    if scarcity_event.event_id != decision.scarcity_event_id:
        raise CiboCompoundCapitalError(
            "compound cycle scarcity/decision identity drift"
        )
    if scarcity_event.decision_at != decision.decision_at:
        raise CiboCompoundCapitalError(
            "compound cycle scarcity/decision time drift"
        )
    if scarcity_event.account_identity != state.account_identity:
        raise CiboCompoundCapitalError(
            "compound cycle scarcity account drift"
        )

    current_snapshot = build_genc6_portfolio_state(
        snapshot_id=scarcity_event.portfolio_state.snapshot_id,
        decision_at=decision.decision_at,
        portfolio=state.core_portfolio,
        t19_ledger=state.t19_ledger,
        context_facts=scarcity_event.portfolio_state.context_facts,
    )
    current_sha = genc6_portfolio_state_sha256(current_snapshot)
    if current_sha != decision.portfolio_state_sha256:
        raise CiboCompoundCapitalError(
            "compound cycle current portfolio differs from sealed GEN-C6 state"
        )
    if current_snapshot.t19_ledger_sha256 != decision.t19_ledger_sha256:
        raise CiboCompoundCapitalError(
            "compound cycle current T19 differs from sealed GEN-C6 state"
        )
    expected = evaluate_genc6_internal_capital_market_shadow(
        event=scarcity_event,
        decision_id=decision.decision_id,
    )
    if expected != decision:
        raise CiboCompoundCapitalError(
            "compound cycle GEN-C6 decision cannot be reproduced"
        )

    market_record = CompoundCycleMarketRecord(
        event_id=event_id,
        occurred_at=decision.decision_at,
        decision_id=decision.decision_id,
        action=decision.treatment_action.value,
        candidate_id=decision.treatment_candidate_id,
        amount_usd=decision.treatment_amount_usd,
        scarcity_event_id=decision.scarcity_event_id,
        portfolio_state_sha256=decision.portfolio_state_sha256,
        t19_ledger_sha256=decision.t19_ledger_sha256,
    )

    if decision.treatment_action is Genc6Action.RESERVE_NO_DEPLOYMENT:
        if source_lot_id is not None:
            raise CiboCompoundCapitalError(
                "reserve action cannot consume a compound source lot"
            )
        return replace(
            state,
            market_records=state.market_records + (market_record,),
            event_ids=state.event_ids + (event_id,),
            last_event_at=decision.decision_at,
        )

    if source_lot_id is None:
        raise CiboCompoundCapitalError(
            "GEN-C6 allocation requires compound source lot"
        )
    candidate = _selected_candidate(scarcity_event, decision)
    source = state.compound_ledger.lot(source_lot_id)
    if source.state is not CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY:
        raise CiboCompoundCapitalError(
            "GEN-C6 allocation requires ACTIVE_COMPOUND_CAPACITY"
        )
    if decision.treatment_amount_usd > source.amount_usd:
        raise CiboCompoundCapitalError(
            "GEN-C6 allocation exceeds source compound lot"
        )

    reservation = PortfolioAllocationReservation(
        signal_fingerprint=candidate.signal_fingerprint,
        trader_id=candidate.trader_id,
        qore_symbol=candidate.qore_symbol,
        stop_risk_usd=candidate.stop_risk_usd,
        margin_usd=candidate.margin_usd,
        concentration_group=candidate.concentration_group,
        concentration_risk_usd=candidate.concentration_risk_usd,
        state=PortfolioAllocationReservationState.ACTIVE,
    )
    t19 = replace(
        state.t19_ledger,
        reservations=state.t19_ledger.reservations + (reservation,),
    )

    remainder = source.amount_usd - decision.treatment_amount_usd
    deployed_lot_id = f"{event_id}:deployed"
    ledger = state.compound_ledger.transition(
        source_lot_id=source_lot_id,
        to_state=CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL,
        amount_usd=decision.treatment_amount_usd,
        moved_lot_id=deployed_lot_id,
        remainder_lot_id=(
            f"{event_id}:remainder" if remainder > 0 else None
        ),
        event_id=f"{event_id}:deploy",
        occurred_at=decision.decision_at,
    )
    deployment = CompoundCycleDeployment(
        deployment_id=f"{event_id}:deployment",
        market_event_id=event_id,
        decision_id=decision.decision_id,
        candidate_id=candidate.candidate_id,
        deployed_at=decision.decision_at,
        trader_id=candidate.trader_id,
        signal_fingerprint=candidate.signal_fingerprint,
        source_lot_id=source_lot_id,
        deployed_lot_id=deployed_lot_id,
        amount_usd=decision.treatment_amount_usd,
        source_generation=source.generation,
        stop_risk_usd=candidate.stop_risk_usd,
        margin_usd=candidate.margin_usd,
    )
    return replace(
        state,
        compound_ledger=ledger,
        t19_ledger=t19,
        market_records=state.market_records + (market_record,),
        deployments=state.deployments + (deployment,),
        event_ids=state.event_ids + (event_id,),
        last_event_at=decision.decision_at,
    )


def settle_compound_deployment(
    state: CiboCompoundCycleState,
    *,
    event_id: str,
    occurred_at: datetime,
    deployment_id: str,
    settlement: CmaSettlementState,
) -> CiboCompoundCycleState:
    """Settle one deployed compound lot, release T19 and create GEN-N profit."""

    require_event_order(state, event_id, occurred_at)
    require_terminal_settlement(settlement)
    deployment = _deployment(state, deployment_id)
    if deployment.settled:
        raise CiboCompoundCapitalError(
            "compound cycle deployment already settled"
        )
    if settlement.signal_fingerprint != deployment.signal_fingerprint:
        raise CiboCompoundCapitalError(
            "compound cycle deployment settlement signal drift"
        )

    digest = settlement_sha256(settlement)
    require_new_settlement(state, digest)
    deployed = state.compound_ledger.lot(deployment.deployed_lot_id)
    pnl = settlement.realized_net_pnl_usd
    loss = -pnl if pnl < 0 else Decimal(0)
    consumed = min(loss, deployed.amount_usd)
    returned = deployed.amount_usd - consumed
    excess_base_loss = max(Decimal(0), loss - deployed.amount_usd)
    if excess_base_loss > state.current_original_base_usd:
        raise CiboCompoundCapitalError(
            "compound cycle loss exceeds compound and original capital"
        )

    ledger = state.compound_ledger.settle_deployment(
        source_lot_id=deployment.deployed_lot_id,
        returned_capacity_usd=returned,
        event_id=f"{event_id}:settle",
        occurred_at=occurred_at,
        returned_lot_id=(
            f"{event_id}:released" if returned > 0 else None
        ),
        consumed_lot_id=(
            f"{event_id}:consumed" if consumed > 0 else None
        ),
    )
    if returned > 0:
        ledger = ledger.transition(
            source_lot_id=f"{event_id}:released",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=returned,
            moved_lot_id=f"{event_id}:recycled",
            event_id=f"{event_id}:recycle",
            occurred_at=occurred_at,
        )

    gains = state.cumulative_realized_gains_usd
    losses = state.cumulative_realized_losses_usd
    base = state.current_original_base_usd

    if pnl > 0:
        evidence = profit_evidence_from_settlement(
            state=state,
            evidence_id=f"{event_id}:profit",
            occurred_at=occurred_at,
            trader_id=deployment.trader_id,
            settlement=settlement,
            settlement_digest=digest,
        )
        next_generation = create_realized_profit_lot(
            evidence,
            lot_id=f"{event_id}:next-generation",
            created_at=occurred_at,
            parent_lots=(deployed,),
        )
        ledger = ledger.admit_realized_profit(
            next_generation,
            event_id=f"{event_id}:admit-next-generation",
            occurred_at=occurred_at,
        )
        gains += pnl
    elif pnl < 0:
        losses += loss
        base -= excess_base_loss

    t19 = state.t19_ledger.release(deployment.signal_fingerprint)
    settled_deployment = replace(
        deployment,
        settled=True,
        settlement_sha256=digest,
    )
    deployments = tuple(
        settled_deployment
        if item.deployment_id == deployment.deployment_id
        else item
        for item in state.deployments
    )
    record = CompoundCycleSettlementRecord(
        event_id=event_id,
        occurred_at=occurred_at,
        source_kind="COMPOUND_CAPITAL",
        trader_id=deployment.trader_id,
        signal_fingerprint=settlement.signal_fingerprint,
        position_id=settlement.position_id,
        settlement_sha256=digest,
        realized_net_pnl_usd=pnl,
        deployment_id=deployment.deployment_id,
    )
    return replace(
        state,
        current_original_base_usd=base,
        compound_ledger=ledger,
        t19_ledger=t19,
        settlements=state.settlements + (record,),
        deployments=deployments,
        event_ids=state.event_ids + (event_id,),
        cumulative_realized_gains_usd=gains,
        cumulative_realized_losses_usd=losses,
        last_event_at=occurred_at,
    )


def _selected_candidate(
    event: CapitalScarcityEvent,
    decision: Genc6InternalCapitalMarketDecision,
) -> Genc6MarginalCapitalCandidate:
    candidate_id = decision.treatment_candidate_id
    if candidate_id is None:
        raise CiboCompoundCapitalError(
            "compound cycle allocation is missing candidate id"
        )
    rows = tuple(
        item for item in event.candidates if item.candidate_id == candidate_id
    )
    if len(rows) != 1:
        raise CiboCompoundCapitalError(
            "compound cycle selected candidate not found exactly once"
        )
    candidate = rows[0]
    if candidate_id not in decision.legal_candidate_ids:
        raise CiboCompoundCapitalError(
            "compound cycle selected candidate is outside legal action set"
        )
    if candidate.requested_capital_usd != decision.treatment_amount_usd:
        raise CiboCompoundCapitalError(
            "compound cycle selected candidate amount drift"
        )
    return candidate


def _deployment(
    state: CiboCompoundCycleState,
    deployment_id: str,
) -> CompoundCycleDeployment:
    rows = tuple(
        item
        for item in state.deployments
        if item.deployment_id == deployment_id
    )
    if len(rows) != 1:
        raise CiboCompoundCapitalError(
            "compound cycle deployment not found"
        )
    return rows[0]
