"""Portfolio allocation ledger for CE2I T09/T18.

Converts pure opportunity competition into explicit CIBO reservations of shared
stop-risk, margin and concentration capacity. Research-only; no broker action.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
    OpportunityAllocationBudget,
    OpportunityAllocationDecision,
    allocate_competing_opportunities,
)


class PortfolioAllocationReservationState(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


@dataclass(frozen=True, slots=True)
class PortfolioAllocationReservation:
    signal_fingerprint: str
    trader_id: TraderLineage
    qore_symbol: str
    stop_risk_usd: Decimal
    margin_usd: Decimal
    concentration_group: str
    concentration_risk_usd: Decimal
    state: PortfolioAllocationReservationState

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "allocation reservation signal/symbol required"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "allocation reservation trader invalid"
            )
        if not self.concentration_group:
            raise CiboCapitalManagementError(
                "allocation concentration group required"
            )
        for name in (
            "stop_risk_usd",
            "margin_usd",
            "concentration_risk_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite positive Decimal"
                )
        if type(self.state) is not PortfolioAllocationReservationState:
            raise CiboCapitalManagementError(
                "allocation reservation state invalid"
            )


@dataclass(frozen=True, slots=True)
class PortfolioAllocationLedger:
    total_stop_risk_capacity_usd: Decimal
    total_margin_capacity_usd: Decimal
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...]
    reservations: tuple[PortfolioAllocationReservation, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "total_stop_risk_capacity_usd",
            "total_margin_capacity_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )
        groups = tuple(name for name, _ in self.concentration_limit_by_group)
        if len(groups) != len(set(groups)):
            raise CiboCapitalManagementError(
                "duplicate allocation concentration group"
            )
        for group, limit in self.concentration_limit_by_group:
            if not group:
                raise CiboCapitalManagementError(
                    "allocation concentration group required"
                )
            if (
                not isinstance(limit, Decimal)
                or not limit.is_finite()
                or limit < 0
            ):
                raise CiboCapitalManagementError(
                    "allocation concentration limit invalid"
                )
        active_ids = tuple(
            item.signal_fingerprint
            for item in self.reservations
            if item.state is PortfolioAllocationReservationState.ACTIVE
        )
        if len(active_ids) != len(set(active_ids)):
            raise CiboCapitalManagementError(
                "duplicate active portfolio allocation reservation"
            )
        if self.used_stop_risk_usd > self.total_stop_risk_capacity_usd:
            raise CiboCapitalManagementError(
                "portfolio allocation exceeds stop-risk capacity"
            )
        if self.used_margin_usd > self.total_margin_capacity_usd:
            raise CiboCapitalManagementError(
                "portfolio allocation exceeds margin capacity"
            )
        for group, used in self.active_concentration_by_group:
            active_limit = self.concentration_limit(group)
            if active_limit is not None and used > active_limit:
                raise CiboCapitalManagementError(
                    "portfolio allocation exceeds concentration capacity"
                )

    @property
    def active_reservations(
        self,
    ) -> tuple[PortfolioAllocationReservation, ...]:
        return tuple(
            item
            for item in self.reservations
            if item.state is PortfolioAllocationReservationState.ACTIVE
        )

    @property
    def used_stop_risk_usd(self) -> Decimal:
        return sum(
            (item.stop_risk_usd for item in self.active_reservations),
            Decimal(0),
        )

    @property
    def used_margin_usd(self) -> Decimal:
        return sum(
            (item.margin_usd for item in self.active_reservations),
            Decimal(0),
        )

    @property
    def active_concentration_by_group(
        self,
    ) -> tuple[tuple[str, Decimal], ...]:
        totals: dict[str, Decimal] = {}
        for item in self.active_reservations:
            totals[item.concentration_group] = (
                totals.get(item.concentration_group, Decimal(0))
                + item.concentration_risk_usd
            )
        return tuple(sorted(totals.items()))

    def concentration_limit(self, group: str) -> Decimal | None:
        for name, limit in self.concentration_limit_by_group:
            if name == group:
                return limit
        return None

    def remaining_budget(self) -> OpportunityAllocationBudget:
        used_by_group = dict(self.active_concentration_by_group)
        remaining_groups = tuple(
            (
                group,
                max(Decimal(0), limit - used_by_group.get(group, Decimal(0))),
            )
            for group, limit in self.concentration_limit_by_group
        )
        return OpportunityAllocationBudget(
            stop_risk_headroom_usd=max(
                Decimal(0),
                self.total_stop_risk_capacity_usd - self.used_stop_risk_usd,
            ),
            margin_headroom_usd=max(
                Decimal(0),
                self.total_margin_capacity_usd - self.used_margin_usd,
            ),
            concentration_limit_by_group=remaining_groups,
        )

    def allocate_and_reserve(
        self,
        candidates: tuple[CapitalOpportunityCandidate, ...],
    ) -> tuple[PortfolioAllocationLedger, OpportunityAllocationDecision]:
        """Compete against remaining capacity and reserve all winners atomically."""

        active_signals = {
            item.signal_fingerprint for item in self.active_reservations
        }
        if any(
            candidate.signal_fingerprint in active_signals
            for candidate in candidates
        ):
            raise CiboCapitalManagementError(
                "candidate already has active portfolio allocation reservation"
            )

        decision = allocate_competing_opportunities(
            candidates,
            self.remaining_budget(),
        )
        by_signal = {
            item.signal_fingerprint: item for item in candidates
        }
        additions = tuple(
            PortfolioAllocationReservation(
                signal_fingerprint=fingerprint,
                trader_id=by_signal[fingerprint].trader_id,
                qore_symbol=by_signal[fingerprint].qore_symbol,
                stop_risk_usd=by_signal[fingerprint].stop_risk_usd,
                margin_usd=by_signal[fingerprint].margin_usd,
                concentration_group=by_signal[fingerprint].concentration_group,
                concentration_risk_usd=(
                    by_signal[fingerprint].concentration_risk_usd
                ),
                state=PortfolioAllocationReservationState.ACTIVE,
            )
            for fingerprint in decision.selected_signal_fingerprints
        )
        next_ledger = replace(
            self,
            reservations=self.reservations + additions,
        )
        return next_ledger, decision

    def release(self, signal_fingerprint: str) -> PortfolioAllocationLedger:
        found = tuple(
            item
            for item in self.reservations
            if item.signal_fingerprint == signal_fingerprint
            and item.state is PortfolioAllocationReservationState.ACTIVE
        )
        if len(found) != 1:
            raise CiboCapitalManagementError(
                "active portfolio allocation reservation not found"
            )
        target = found[0]
        return replace(
            self,
            reservations=tuple(
                replace(
                    item,
                    state=PortfolioAllocationReservationState.RELEASED,
                )
                if item is target
                else item
                for item in self.reservations
            ),
        )
