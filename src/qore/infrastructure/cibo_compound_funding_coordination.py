"""Coordinate Compound Portfolio ownership with Source Ledger risk funding.

GEN-C6 deploys economic capital from a compound lot. The Source Ledger does not
reserve that full economic allocation again; it reserves the sealed plausible
loss (stop-risk) that the realized-profit source must fund. T19 independently
tracks stop-risk and margin capacity.

Research/shadow only. No productive authority is granted.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementState
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_cycle_state import CiboCompoundCycleState
from qore.infrastructure.cibo_compound_market_cycle import (
    apply_internal_capital_market_decision,
    settle_compound_deployment,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    IntegratedCapitalTruth,
    ProtectedOpenFloorEquivalenceBinding,
    RealizedProfitEquivalenceBinding,
    build_integrated_capital_truth,
)
from qore.infrastructure.cibo_internal_capital_market import (
    CapitalScarcityEvent,
    Genc6Action,
    Genc6InternalCapitalMarketDecision,
    Genc6MarginalCapitalCandidate,
)


@dataclass(frozen=True, slots=True)
class CompoundRiskFundingLink:
    deployment_id: str
    source_id: str
    source_reservation_id: str
    funded_stop_risk_usd: Decimal
    settled: bool = False

    def __post_init__(self) -> None:
        if (
            not self.deployment_id
            or not self.source_id
            or not self.source_reservation_id
        ):
            raise CiboCompoundCapitalError(
                "compound risk-funding link identity is required"
            )
        if (
            not isinstance(self.funded_stop_risk_usd, Decimal)
            or not self.funded_stop_risk_usd.is_finite()
            or self.funded_stop_risk_usd <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound funded stop risk must be positive Decimal"
            )
        if type(self.settled) is not bool:
            raise CiboCompoundCapitalError(
                "compound risk-funding settled flag must be bool"
            )


@dataclass(frozen=True, slots=True)
class IntegratedCompoundFundingState:
    cycle: CiboCompoundCycleState
    source_ledger: CapitalSourceLedger
    realized_profit_bindings: tuple[
        RealizedProfitEquivalenceBinding, ...
    ]
    protected_floor_bindings: tuple[
        ProtectedOpenFloorEquivalenceBinding, ...
    ] = ()
    funding_links: tuple[CompoundRiskFundingLink, ...] = ()
    runtime_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.cycle, CiboCompoundCycleState):
            raise CiboCompoundCapitalError(
                "integrated funding requires canonical compound cycle"
            )
        if not isinstance(self.source_ledger, CapitalSourceLedger):
            raise CiboCompoundCapitalError(
                "integrated funding requires canonical source ledger"
            )
        link_ids = tuple(item.deployment_id for item in self.funding_links)
        reservation_ids = tuple(
            item.source_reservation_id for item in self.funding_links
        )
        if (
            len(link_ids) != len(set(link_ids))
            or len(reservation_ids) != len(set(reservation_ids))
        ):
            raise CiboCompoundCapitalError(
                "integrated funding links must be unique"
            )
        if any(
            (
                self.runtime_authority,
                self.risk_authority,
                self.execution_authority,
            )
        ):
            raise CiboCompoundCapitalError(
                "integrated funding has no productive authority"
            )
        _ = self.capital_truth

    @property
    def capital_truth(self) -> IntegratedCapitalTruth:
        return build_integrated_capital_truth(
            account_identity=self.cycle.account_identity,
            source_ledger=self.source_ledger,
            compound_state=self.cycle,
            realized_profit_bindings=self.realized_profit_bindings,
            protected_floor_bindings=self.protected_floor_bindings,
        )


def apply_funded_internal_market_decision(
    state: IntegratedCompoundFundingState,
    *,
    event_id: str,
    scarcity_event: CapitalScarcityEvent,
    decision: Genc6InternalCapitalMarketDecision,
    source_lot_id: str | None = None,
) -> IntegratedCompoundFundingState:
    """Apply GEN-C6 and reserve only its sealed loss funding in Source Ledger."""

    if decision.treatment_action is Genc6Action.RESERVE_NO_DEPLOYMENT:
        cycle = apply_internal_capital_market_decision(
            state.cycle,
            event_id=event_id,
            scarcity_event=scarcity_event,
            decision=decision,
            source_lot_id=None,
        )
        return replace(state, cycle=cycle)

    if source_lot_id is None:
        raise CiboCompoundCapitalError(
            "funded compound allocation requires source lot"
        )
    candidate = _selected_candidate(scarcity_event, decision)
    source_id = _realized_source_for_lot(state, source_lot_id)
    source_account = tuple(
        item for item in state.source_ledger.accounts
        if item.source_id == source_id
    )
    if (
        len(source_account) != 1
        or source_account[0].source is not CapitalSource.REALIZED_PROFIT
    ):
        raise CiboCompoundCapitalError(
            "compound risk funding requires realized-profit source"
        )

    reservation_id = f"{event_id}:source-risk"
    source_ledger = (
        state.source_ledger
        .reserve(
            reservation_id=reservation_id,
            source_id=source_id,
            amount_usd=candidate.stop_risk_usd,
        )
        .deploy(reservation_id)
    )
    cycle = apply_internal_capital_market_decision(
        state.cycle,
        event_id=event_id,
        scarcity_event=scarcity_event,
        decision=decision,
        source_lot_id=source_lot_id,
    )
    deployment_id = f"{event_id}:deployment"
    link = CompoundRiskFundingLink(
        deployment_id=deployment_id,
        source_id=source_id,
        source_reservation_id=reservation_id,
        funded_stop_risk_usd=candidate.stop_risk_usd,
        settled=False,
    )
    updated = replace(
        state,
        cycle=cycle,
        source_ledger=source_ledger,
        funding_links=state.funding_links + (link,),
    )
    _ = updated.capital_truth
    return updated


def settle_funded_compound_deployment(
    state: IntegratedCompoundFundingState,
    *,
    event_id: str,
    occurred_at,
    deployment_id: str,
    settlement: CmaSettlementState,
) -> IntegratedCompoundFundingState:
    """Settle Compound/T19 and Source Ledger from the same realized PnL."""

    link = _funding_link(state, deployment_id)
    if link.settled:
        raise CiboCompoundCapitalError(
            "compound risk-funding link already settled"
        )
    pnl = settlement.realized_net_pnl_usd
    loss = -pnl if pnl < 0 else Decimal(0)
    if loss > link.funded_stop_risk_usd:
        raise CiboCompoundCapitalError(
            "integrated funding loss exceeds funded stop risk; "
            "additional loss provenance is required"
        )

    returned_risk = link.funded_stop_risk_usd - loss
    source_ledger = state.source_ledger.settle_deployment(
        link.source_reservation_id,
        returned_capacity_usd=returned_risk,
    )
    cycle = settle_compound_deployment(
        state.cycle,
        event_id=event_id,
        occurred_at=occurred_at,
        deployment_id=deployment_id,
        settlement=settlement,
    )

    bindings = state.realized_profit_bindings
    if pnl > 0:
        new_source_id = f"{event_id}:realized-profit-source"
        new_lot_id = f"{event_id}:next-generation"
        source_ledger = source_ledger.add_source(
            source_id=new_source_id,
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=pnl,
        )
        bindings = bindings + (
            RealizedProfitEquivalenceBinding(
                source_id=new_source_id,
                admission_lot_ids=(new_lot_id,),
            ),
        )

    settled_link = replace(link, settled=True)
    links = tuple(
        settled_link if item.deployment_id == deployment_id else item
        for item in state.funding_links
    )
    updated = replace(
        state,
        cycle=cycle,
        source_ledger=source_ledger,
        realized_profit_bindings=bindings,
        funding_links=links,
    )
    _ = updated.capital_truth
    return updated


def _selected_candidate(
    event: CapitalScarcityEvent,
    decision: Genc6InternalCapitalMarketDecision,
) -> Genc6MarginalCapitalCandidate:
    candidate_id = decision.treatment_candidate_id
    if candidate_id is None:
        raise CiboCompoundCapitalError(
            "funded compound allocation lacks candidate"
        )
    rows = tuple(
        item for item in event.candidates
        if item.candidate_id == candidate_id
    )
    if len(rows) != 1:
        raise CiboCompoundCapitalError(
            "funded compound candidate is not unique"
        )
    return rows[0]


def _realized_source_for_lot(
    state: IntegratedCompoundFundingState,
    source_lot_id: str,
) -> str:
    lot = state.cycle.compound_ledger.lot(source_lot_id)
    ancestry = set(lot.parent_lot_ids + (lot.lot_id,))
    source_ids = {
        binding.source_id
        for binding in state.realized_profit_bindings
        if any(
            admission_id in ancestry
            for admission_id in binding.admission_lot_ids
        )
    }
    if len(source_ids) != 1:
        raise CiboCompoundCapitalError(
            "compound lot lacks unique realized-profit funding lineage"
        )
    return next(iter(source_ids))


def _funding_link(
    state: IntegratedCompoundFundingState,
    deployment_id: str,
) -> CompoundRiskFundingLink:
    rows = tuple(
        item for item in state.funding_links
        if item.deployment_id == deployment_id
    )
    if len(rows) != 1:
        raise CiboCompoundCapitalError(
            "compound deployment funding link not found"
        )
    return rows[0]
