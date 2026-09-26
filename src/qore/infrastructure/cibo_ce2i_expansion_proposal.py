"""CE2I expansion proposal and capital-reservation lifecycle.

Research-only. This module can:
- transform a reconciled CMA CAPITALIZE observation into one bounded expansion plan;
- reserve exactly one proven non-base capital source atomically;
- build the independent QORE Risk request;
- deploy/release/settle the reservation in the durable capital ledger.

It never mutates broker state and never bypasses QORE Risk.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal

from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalCapacityDimension,
    CapitalSource,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    capital_source_dimension,
    plan_self_financing_expansion,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalSourceAccount,
    ReservationState,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request

_ELIGIBLE_EXPANSION_SOURCES = {
    CapitalSource.REALIZED_PROFIT,
    CapitalSource.PROTECTED_ECONOMIC_FLOOR,
}


@dataclass(frozen=True, slots=True)
class CmaExpansionProposal:
    reservation_id: str
    source_id: str
    source: CapitalSource
    plan: CiboCapitalActionPlan
    risk_request: CiboRiskRequest
    ledger_generation: int

    def __post_init__(self) -> None:
        if not self.reservation_id or not self.source_id:
            raise CiboCapitalManagementError("reservation/source id required")
        if self.source not in _ELIGIBLE_EXPANSION_SOURCES:
            raise CiboCapitalManagementError("expansion source not eligible")
        if self.plan.action is not CapitalAction.EXPAND:
            raise CiboCapitalManagementError("proposal plan must be EXPAND")
        if self.plan.capital_source is not self.source:
            raise CiboCapitalManagementError("proposal source mismatch")
        if self.ledger_generation <= 0:
            raise CiboCapitalManagementError(
                "proposal must reference persisted ledger generation"
            )


def reserve_expansion_proposal(
    *,
    reservation_id: str,
    source_id: str,
    opportunity: TraderOpportunityEnvelope,
    observation: CmaCapitalObservation,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    assigned_capital_usd: Decimal,
    requested_at: datetime,
    expires_at: datetime,
    request_id: str,
    ledger_store: DurableCapitalSourceLedgerStore,
    maximum_expansion_volume: Decimal | None = None,
) -> CmaExpansionProposal:
    """Atomically reserve one proven source and construct the Risk request."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "opportunity must be TraderOpportunityEnvelope"
        )
    if not isinstance(observation, CmaCapitalObservation):
        raise CiboCapitalManagementError(
            "observation must be CmaCapitalObservation"
        )
    if not isinstance(ledger_store, DurableCapitalSourceLedgerStore):
        raise CiboCapitalManagementError(
            "ledger_store must be DurableCapitalSourceLedgerStore"
        )
    if not reservation_id or not source_id:
        raise CiboCapitalManagementError("reservation/source id required")
    if observation.signal_fingerprint != opportunity.signal_fingerprint:
        raise CiboCapitalManagementError("observation/opportunity signal mismatch")
    if observation.symbol != opportunity.qore_symbol:
        raise CiboCapitalManagementError("observation/opportunity symbol mismatch")
    if TraderLineage(observation.trader) is not opportunity.trader_id:
        raise CiboCapitalManagementError("observation/opportunity trader mismatch")
    if (
        not observation.evidence_sufficient
        or not observation.expansion_eligible
        or observation.self_financing_capacity_usd is None
        or observation.base_capital_at_risk_usd is None
        or observation.base_capital_at_risk_usd > 0
    ):
        raise CiboCapitalManagementError(
            "CMA observation is not eligible for expansion"
        )

    bounded_opportunity = _bounded_opportunity(
        opportunity,
        maximum_expansion_volume=maximum_expansion_volume,
    )

    version = ledger_store.load()
    account = _source_account(version, source_id)
    if (
        account.source not in _ELIGIBLE_EXPANSION_SOURCES
        or capital_source_dimension(account.source)
        is not CapitalCapacityDimension.ECONOMIC_PROFIT_CAPITAL
    ):
        raise CiboCapitalManagementError(
            "ledger source is not eligible for self-financing expansion"
        )

    observed_source_capacity = _observed_capacity_for_source(
        observation,
        account.source,
    )
    usable_source_capacity = min(
        observation.self_financing_capacity_usd,
        observed_source_capacity,
        account.available_usd,
    )
    if usable_source_capacity <= 0:
        raise CiboCapitalManagementError(
            "selected source has no reconciled available expansion capacity"
        )

    capital = _capital_state_for_source(
        source=account.source,
        source_capacity_usd=usable_source_capacity,
        assigned_capital_usd=assigned_capital_usd,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
    )
    plan = plan_self_financing_expansion(bounded_opportunity, capital)
    if plan.action is not CapitalAction.EXPAND:
        raise CiboCapitalManagementError(
            f"CIBO expansion unavailable: {plan.reason}"
        )
    if plan.capital_source is not account.source:
        raise CiboCapitalManagementError(
            "planner selected a different source than reserved ledger account"
        )
    if plan.stop_risk_usd > usable_source_capacity:
        raise CiboCapitalManagementError(
            "planned risk exceeds reconciled source capacity"
        )

    risk_request = build_cma_risk_request(
        request_id=request_id,
        opportunity=bounded_opportunity,
        plan=plan,
        requested_at=requested_at,
        expires_at=expires_at,
        capital_source_id=source_id,
    )

    reserved = version.ledger.reserve(
        reservation_id=reservation_id,
        source_id=source_id,
        amount_usd=plan.stop_risk_usd,
    )
    stored = ledger_store.store(
        reserved,
        expected_generation=version.generation,
    )
    return CmaExpansionProposal(
        reservation_id=reservation_id,
        source_id=source_id,
        source=account.source,
        plan=plan,
        risk_request=risk_request,
        ledger_generation=stored.generation,
    )


def deploy_reserved_expansion(
    *,
    reservation_id: str,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> VersionedCapitalSourceLedger:
    """Mark a Risk/execution-approved reservation as economically deployed."""

    version = ledger_store.load()
    deployed = version.ledger.deploy(reservation_id)
    return ledger_store.store(
        deployed,
        expected_generation=version.generation,
    )


def release_rejected_expansion(
    *,
    reservation_id: str,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> VersionedCapitalSourceLedger:
    """Release a reservation when Risk/execution did not deploy it."""

    version = ledger_store.load()
    released = version.ledger.release_unused(reservation_id)
    return ledger_store.store(
        released,
        expected_generation=version.generation,
    )


def settle_expansion_capacity(
    *,
    reservation_id: str,
    returned_capacity_usd: Decimal,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> VersionedCapitalSourceLedger:
    """Settle deployed expansion capacity after authoritative reconciliation."""

    version = ledger_store.load()
    settled = version.ledger.settle_deployment(
        reservation_id,
        returned_capacity_usd=returned_capacity_usd,
    )
    return ledger_store.store(
        settled,
        expected_generation=version.generation,
    )


def reservation_state(
    proposal: CmaExpansionProposal,
    *,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> ReservationState:
    """Return the durable state for one proposal reservation."""

    version = ledger_store.load()
    found = tuple(
        item
        for item in version.ledger.reservations
        if item.reservation_id == proposal.reservation_id
    )
    if len(found) != 1:
        raise CiboCapitalManagementError("proposal reservation not found")
    return found[0].state


def _source_account(
    version: VersionedCapitalSourceLedger,
    source_id: str,
) -> CapitalSourceAccount:
    found = tuple(
        item for item in version.ledger.accounts if item.source_id == source_id
    )
    if len(found) != 1:
        raise CiboCapitalManagementError("capital source not found")
    return found[0]


def _observed_capacity_for_source(
    observation: CmaCapitalObservation,
    source: CapitalSource,
) -> Decimal:
    if source is CapitalSource.REALIZED_PROFIT:
        return max(Decimal(0), observation.realized_net_pnl_usd)
    if source is CapitalSource.PROTECTED_ECONOMIC_FLOOR:
        return max(
            Decimal(0),
            observation.protected_open_floor_usd or Decimal(0),
        )
    raise CiboCapitalManagementError("unsupported expansion source")


def _capital_state_for_source(
    *,
    source: CapitalSource,
    source_capacity_usd: Decimal,
    assigned_capital_usd: Decimal,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
) -> CiboCapitalState:
    for name, value in (
        ("source_capacity_usd", source_capacity_usd),
        ("assigned_capital_usd", assigned_capital_usd),
        ("hard_risk_headroom_usd", hard_risk_headroom_usd),
        ("margin_headroom_usd", margin_headroom_usd),
    ):
        if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
            raise CiboCapitalManagementError(
                f"{name} must be finite non-negative Decimal"
            )
    if assigned_capital_usd <= 0:
        raise CiboCapitalManagementError("assigned_capital_usd must be positive")

    realized = (
        source_capacity_usd
        if source is CapitalSource.REALIZED_PROFIT
        else Decimal(0)
    )
    protected = (
        source_capacity_usd
        if source is CapitalSource.PROTECTED_ECONOMIC_FLOOR
        else Decimal(0)
    )
    return CiboCapitalState(
        assigned_capital_usd=assigned_capital_usd,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        base_capital_at_risk_usd=Decimal(0),
        realized_net_profit_usd=realized,
        protected_open_economic_floor_usd=protected,
        proven_self_financing_capacity_usd=source_capacity_usd,
        reserved_expansion_risk_usd=Decimal(0),
        cost_reserve_usd=Decimal(0),
    )



def _bounded_opportunity(
    opportunity: TraderOpportunityEnvelope,
    *,
    maximum_expansion_volume: Decimal | None,
) -> TraderOpportunityEnvelope:
    if maximum_expansion_volume is None:
        return opportunity
    if (
        not isinstance(maximum_expansion_volume, Decimal)
        or not maximum_expansion_volume.is_finite()
        or maximum_expansion_volume < 0
    ):
        raise CiboCapitalManagementError(
            "maximum_expansion_volume must be finite non-negative Decimal/null"
        )
    raw = min(maximum_expansion_volume, opportunity.maximum_volume)
    steps = (raw / opportunity.volume_step).to_integral_value(
        rounding=ROUND_FLOOR
    )
    bounded = steps * opportunity.volume_step
    if bounded < opportunity.minimum_volume:
        raise CiboCapitalManagementError(
            "execution-efficient cap cannot express provider minimum volume"
        )
    return replace(opportunity, maximum_volume=bounded)
