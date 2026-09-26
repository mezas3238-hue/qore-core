"""Atomic multi-source CE2I expansion funding.

Combines multiple reconciled ECONOMIC_PROFIT_CAPITAL accounts into one CIBO
expansion without double-counting observed capital evidence.

Research-only. It creates a CiboRiskRequest but never mutates broker state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal

from qore.infrastructure.account_wide_risk import CiboRiskRequest
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalCapacityDimension,
    CapitalSource,
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
    capital_source_dimension,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalReservationRequest,
    CapitalSourceAccount,
    ReservationState,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation


@dataclass(frozen=True, slots=True)
class CmaFundingSlice:
    reservation_id: str
    source_id: str
    source: CapitalSource
    amount_usd: Decimal

    def __post_init__(self) -> None:
        if not self.reservation_id or not self.source_id:
            raise CiboCapitalManagementError("funding slice ids required")
        if self.source not in {
            CapitalSource.REALIZED_PROFIT,
            CapitalSource.PROTECTED_ECONOMIC_FLOOR,
        }:
            raise CiboCapitalManagementError(
                "multi-source expansion slice must be economic profit capital"
            )
        if (
            not isinstance(self.amount_usd, Decimal)
            or not self.amount_usd.is_finite()
            or self.amount_usd <= 0
        ):
            raise CiboCapitalManagementError(
                "funding slice amount must be finite positive Decimal"
            )


@dataclass(frozen=True, slots=True)
class CmaMultiSourceExpansionProposal:
    reservation_group_id: str
    funding_slices: tuple[CmaFundingSlice, ...]
    volume: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    risk_request: CiboRiskRequest
    ledger_generation: int

    def __post_init__(self) -> None:
        if not self.reservation_group_id:
            raise CiboCapitalManagementError("reservation_group_id required")
        if len(self.funding_slices) < 2:
            raise CiboCapitalManagementError(
                "multi-source proposal requires at least two funding slices"
            )
        if (
            not isinstance(self.volume, Decimal)
            or not self.volume.is_finite()
            or self.volume <= 0
        ):
            raise CiboCapitalManagementError("proposal volume must be positive")
        if sum(
            (item.amount_usd for item in self.funding_slices),
            Decimal(0),
        ) != self.stop_risk_usd:
            raise CiboCapitalManagementError(
                "funding slices must sum exactly to stop risk"
            )
        if self.risk_request.requested_volume != self.volume:
            raise CiboCapitalManagementError(
                "risk request volume must equal multi-source proposal volume"
            )
        if self.ledger_generation <= 0:
            raise CiboCapitalManagementError(
                "proposal must reference persisted ledger generation"
            )


def reserve_multi_source_expansion(
    *,
    reservation_group_id: str,
    request_id: str,
    opportunity: TraderOpportunityEnvelope,
    observation: CmaCapitalObservation,
    assigned_capital_usd: Decimal,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    requested_at: datetime,
    expires_at: datetime,
    ledger_store: DurableCapitalSourceLedgerStore,
    maximum_expansion_volume: Decimal | None = None,
) -> CmaMultiSourceExpansionProposal:
    """Reserve all required funding slices atomically or reserve none."""

    if not reservation_group_id or not request_id:
        raise CiboCapitalManagementError(
            "reservation_group_id/request_id required"
        )
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
    if observation.signal_fingerprint != opportunity.signal_fingerprint:
        raise CiboCapitalManagementError(
            "observation/opportunity signal mismatch"
        )
    if observation.symbol != opportunity.qore_symbol:
        raise CiboCapitalManagementError(
            "observation/opportunity symbol mismatch"
        )
    if (
        not observation.evidence_sufficient
        or not observation.expansion_eligible
        or observation.self_financing_capacity_usd is None
        or observation.self_financing_capacity_usd <= 0
        or observation.base_capital_at_risk_usd is None
        or observation.base_capital_at_risk_usd > 0
    ):
        raise CiboCapitalManagementError(
            "CMA observation is not eligible for multi-source expansion"
        )

    for name, value in (
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
    if expires_at <= requested_at:
        raise CiboCapitalManagementError("expires_at must follow requested_at")

    version = ledger_store.load()
    eligible_accounts = tuple(
        account
        for account in version.ledger.accounts
        if account.available_usd > 0
        and account.source
        in {
            CapitalSource.REALIZED_PROFIT,
            CapitalSource.PROTECTED_ECONOMIC_FLOOR,
        }
        and capital_source_dimension(account.source)
        is CapitalCapacityDimension.ECONOMIC_PROFIT_CAPITAL
    )
    if len(eligible_accounts) < 2:
        raise CiboCapitalManagementError(
            "multi-source expansion requires at least two available economic sources"
        )

    observed_by_source = {
        CapitalSource.REALIZED_PROFIT: max(
            Decimal(0),
            observation.realized_net_pnl_usd,
        ),
        CapitalSource.PROTECTED_ECONOMIC_FLOOR: max(
            Decimal(0),
            observation.protected_open_floor_usd or Decimal(0),
        ),
    }
    ledger_capacity = _bounded_ledger_capacity(
        eligible_accounts,
        observed_by_source=observed_by_source,
    )
    total_capacity = min(
        observation.self_financing_capacity_usd,
        hard_risk_headroom_usd,
        ledger_capacity,
    )
    if total_capacity <= 0:
        raise CiboCapitalManagementError(
            "no reconciled multi-source expansion capacity"
        )

    volume_cap = opportunity.maximum_volume
    if maximum_expansion_volume is not None:
        if (
            not isinstance(maximum_expansion_volume, Decimal)
            or not maximum_expansion_volume.is_finite()
            or maximum_expansion_volume < 0
        ):
            raise CiboCapitalManagementError(
                "maximum_expansion_volume must be finite non-negative Decimal/null"
            )
        volume_cap = min(volume_cap, maximum_expansion_volume)

    by_risk = total_capacity / opportunity.stop_loss_per_volume
    by_margin = margin_headroom_usd / opportunity.margin_per_volume
    raw_volume = min(by_risk, by_margin, volume_cap)
    steps = (raw_volume / opportunity.volume_step).to_integral_value(
        rounding=ROUND_FLOOR
    )
    volume = steps * opportunity.volume_step
    if volume < opportunity.minimum_volume:
        raise CiboCapitalManagementError(
            "combined sources cannot express provider minimum expansion volume"
        )

    stop_risk = volume * opportunity.stop_loss_per_volume
    margin = volume * opportunity.margin_per_volume
    slices = _allocate_funding_slices(
        reservation_group_id=reservation_group_id,
        required_risk_usd=stop_risk,
        accounts=eligible_accounts,
        observed_by_source=observed_by_source,
    )
    if len(slices) < 2:
        raise CiboCapitalManagementError(
            "single source can already fund expansion; multi-source path not required"
        )

    reservation_requests = tuple(
        CapitalReservationRequest(
            reservation_id=item.reservation_id,
            source_id=item.source_id,
            amount_usd=item.amount_usd,
        )
        for item in slices
    )
    reserved = version.ledger.reserve_many(reservation_requests)
    stored = ledger_store.store(
        reserved,
        expected_generation=version.generation,
    )

    risk_request = CiboRiskRequest(
        request_id=request_id,
        trader_id=opportunity.trader_id,
        signal_fingerprint=opportunity.signal_fingerprint,
        qore_symbol=opportunity.qore_symbol,
        provider_symbol=opportunity.provider_symbol,
        side=opportunity.side,
        entry_type=opportunity.entry_type,
        intended_entry=opportunity.intended_entry,
        stop_loss=opportunity.stop_loss,
        take_profit=opportunity.take_profit,
        requested_volume=volume,
        volume_step=opportunity.volume_step,
        minimum_volume=opportunity.minimum_volume,
        stop_loss_per_volume=opportunity.stop_loss_per_volume,
        margin_per_volume=opportunity.margin_per_volume,
        requested_at=requested_at,
        expires_at=expires_at,
        strategy_requested_risk_usd=None,
        minimum_volume_uplifted=False,
    )
    return CmaMultiSourceExpansionProposal(
        reservation_group_id=reservation_group_id,
        funding_slices=slices,
        volume=volume,
        stop_risk_usd=stop_risk,
        margin_usd=margin,
        risk_request=risk_request,
        ledger_generation=stored.generation,
    )


def deploy_multi_source_expansion(
    proposal: CmaMultiSourceExpansionProposal,
    *,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> VersionedCapitalSourceLedger:
    version = ledger_store.load()
    ledger = version.ledger
    for item in proposal.funding_slices:
        ledger = ledger.deploy(item.reservation_id)
    return ledger_store.store(
        ledger,
        expected_generation=version.generation,
    )


def release_multi_source_expansion(
    proposal: CmaMultiSourceExpansionProposal,
    *,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> VersionedCapitalSourceLedger:
    version = ledger_store.load()
    ledger = version.ledger
    for item in proposal.funding_slices:
        ledger = ledger.release_unused(item.reservation_id)
    return ledger_store.store(
        ledger,
        expected_generation=version.generation,
    )


def multi_source_reservation_states(
    proposal: CmaMultiSourceExpansionProposal,
    *,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> tuple[ReservationState, ...]:
    version = ledger_store.load()
    by_id = {
        item.reservation_id: item.state
        for item in version.ledger.reservations
    }
    return tuple(by_id[item.reservation_id] for item in proposal.funding_slices)


def _bounded_ledger_capacity(
    accounts: tuple[CapitalSourceAccount, ...],
    *,
    observed_by_source: dict[CapitalSource, Decimal],
) -> Decimal:
    total = Decimal(0)
    for source in (
        CapitalSource.REALIZED_PROFIT,
        CapitalSource.PROTECTED_ECONOMIC_FLOOR,
    ):
        source_available = sum(
            (
                account.available_usd
                for account in accounts
                if account.source is source
            ),
            Decimal(0),
        )
        total += min(
            source_available,
            observed_by_source.get(source, Decimal(0)),
        )
    return total


def _allocate_funding_slices(
    *,
    reservation_group_id: str,
    required_risk_usd: Decimal,
    accounts: tuple[CapitalSourceAccount, ...],
    observed_by_source: dict[CapitalSource, Decimal],
) -> tuple[CmaFundingSlice, ...]:
    remaining = required_risk_usd
    slices: list[CmaFundingSlice] = []
    source_remaining = dict(observed_by_source)
    ordered = sorted(
        accounts,
        key=lambda account: (
            0 if account.source is CapitalSource.REALIZED_PROFIT else 1,
            -account.available_usd,
            account.source_id,
        ),
    )
    for account in ordered:
        if remaining <= 0:
            break
        observed_remaining = source_remaining.get(account.source, Decimal(0))
        amount = min(
            remaining,
            account.available_usd,
            observed_remaining,
        )
        if amount <= 0:
            continue
        reservation_id = (
            f"{reservation_group_id}:{len(slices) + 1}:{account.source_id}"
        )
        slices.append(
            CmaFundingSlice(
                reservation_id=reservation_id,
                source_id=account.source_id,
                source=account.source,
                amount_usd=amount,
            )
        )
        source_remaining[account.source] = observed_remaining - amount
        remaining -= amount
    if remaining > 0:
        raise CiboCapitalManagementError(
            "multi-source allocation cannot cover required stop risk"
        )
    return tuple(slices)
