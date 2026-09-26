"""Phase 19C normalized-capital numeraire and causal replay contracts.

This module creates a dimensionless CIBO capital unit so portfolio-policy
research can continue without fabricating historical provider economics.

It does NOT turn heterogeneous Trader R into a raw additive portfolio metric.
Instead, CIBO allocates an ex-ante normalized risk-capacity budget to each
opportunity and only the budget-weighted realized result changes the normalized
capital ledger after the historical exit event is reached.

Research-only. No USD equivalence, historical provider economics, QORE Risk
authority, DEMO/LIVE authority or broker mutation is claimed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
)


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")


def _finite(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite Decimal")


def _positive(value: Decimal, *, name: str) -> None:
    _finite(value, name=name)
    if value <= 0:
        raise CiboCapitalManagementError(f"{name} must be positive")


def _nonnegative(value: Decimal, *, name: str) -> None:
    _finite(value, name=name)
    if value < 0:
        raise CiboCapitalManagementError(f"{name} must be non-negative")


class Phase19CapitalNumeraireBasis(StrEnum):
    """What one normalized CIBO risk-capacity unit means."""

    STRUCTURAL_STOP_RISK = "STRUCTURAL_STOP_RISK"


class Phase19NormalizedAllocationStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED_INSUFFICIENT_CAPACITY = "REJECTED_INSUFFICIENT_CAPACITY"
    REJECTED_INSOLVENT_CAPITAL = "REJECTED_INSOLVENT_CAPITAL"


@dataclass(frozen=True, slots=True)
class Phase19CapitalNumeraireContract:
    """Constitution for dimensionless Phase-19 capital arithmetic."""

    contract_id: str
    basis: Phase19CapitalNumeraireBasis = (
        Phase19CapitalNumeraireBasis.STRUCTURAL_STOP_RISK
    )
    unit_name: str = "CIBO_NORMALIZED_RISK_CAPACITY_UNIT"
    provider_economics_required: bool = False
    usd_equivalence_claimed: bool = False
    historical_provider_economics_claimed: bool = False
    margin_equivalence_claimed: bool = False
    cross_trader_raw_r_aggregation_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.contract_id or not self.unit_name:
            raise CiboCapitalManagementError(
                "Phase 19 capital numeraire identity is required"
            )
        if type(self.basis) is not Phase19CapitalNumeraireBasis:
            raise CiboCapitalManagementError(
                "Phase 19 capital numeraire basis is invalid"
            )
        if self.provider_economics_required:
            raise CiboCapitalManagementError(
                "normalized capital numeraire must not require provider economics"
            )
        if (
            self.usd_equivalence_claimed
            or self.historical_provider_economics_claimed
            or self.margin_equivalence_claimed
            or self.cross_trader_raw_r_aggregation_authorized
        ):
            raise CiboCapitalManagementError(
                "normalized capital numeraire cannot claim USD/provider/margin "
                "equivalence or raw cross-Trader R aggregation"
            )


@dataclass(frozen=True, slots=True)
class Phase19NormalizedCapitalAllocation:
    """Ex-ante normalized risk budget produced without future outcome."""

    signal_fingerprint: str
    trader_id: TraderLineage
    decision_at: datetime
    risk_budget_ncu: Decimal
    allocation_priority: int
    policy_id: str
    evidence_id: str
    train_cutoff_at: datetime | None = None
    outcome_aware: bool = False

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.policy_id or not self.evidence_id:
            raise CiboCapitalManagementError(
                "normalized capital allocation identity is required"
            )
        if self.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "normalized capital allocation Trader is outside Phase 19"
            )
        _aware(self.decision_at, name="decision_at")
        _positive(self.risk_budget_ncu, name="risk_budget_ncu")
        if (
            type(self.allocation_priority) is not int
            or self.allocation_priority < 0
        ):
            raise CiboCapitalManagementError(
                "allocation_priority must be non-negative int"
            )
        if self.train_cutoff_at is not None:
            _aware(self.train_cutoff_at, name="train_cutoff_at")
            if self.train_cutoff_at > self.decision_at:
                raise CiboCapitalManagementError(
                    "train cutoff cannot occur after allocation decision"
                )
        if self.outcome_aware:
            raise CiboCapitalManagementError(
                "normalized capital allocation cannot be outcome-aware"
            )


@dataclass(frozen=True, slots=True)
class Phase19NormalizedReplayTrade:
    """One normalized-policy replay record with post-trade outcome isolated."""

    opportunity: Phase19ChronologicalOpportunity
    allocation: Phase19NormalizedCapitalAllocation
    normalized_outcome_r: Decimal
    outcome_evidence_id: str

    def __post_init__(self) -> None:
        if self.opportunity.trader_id is not self.allocation.trader_id:
            raise CiboCapitalManagementError(
                "normalized replay Trader identity mismatch"
            )
        if (
            self.opportunity.signal_fingerprint
            != self.allocation.signal_fingerprint
        ):
            raise CiboCapitalManagementError(
                "normalized replay signal identity mismatch"
            )
        if self.allocation.decision_at > self.opportunity.entry_at:
            raise CiboCapitalManagementError(
                "normalized capital decision cannot occur after entry"
            )
        _finite(self.normalized_outcome_r, name="normalized_outcome_r")
        if not self.outcome_evidence_id:
            raise CiboCapitalManagementError(
                "normalized replay outcome evidence is required"
            )


@dataclass(frozen=True, slots=True)
class Phase19NormalizedCapitalDecision:
    signal_fingerprint: str
    trader_id: TraderLineage
    entry_at: datetime
    exit_at: datetime
    requested_risk_ncu: Decimal
    status: Phase19NormalizedAllocationStatus
    realized_delta_ncu: Decimal | None

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "normalized capital decision signal is required"
            )
        _aware(self.entry_at, name="entry_at")
        _aware(self.exit_at, name="exit_at")
        if self.exit_at <= self.entry_at:
            raise CiboCapitalManagementError(
                "normalized capital decision interval is invalid"
            )
        _positive(self.requested_risk_ncu, name="requested_risk_ncu")
        if type(self.status) is not Phase19NormalizedAllocationStatus:
            raise CiboCapitalManagementError(
                "normalized capital decision status is invalid"
            )
        if self.status is Phase19NormalizedAllocationStatus.ACCEPTED:
            if self.realized_delta_ncu is None:
                raise CiboCapitalManagementError(
                    "accepted normalized allocation requires realized delta"
                )
            _finite(self.realized_delta_ncu, name="realized_delta_ncu")
        elif self.realized_delta_ncu is not None:
            raise CiboCapitalManagementError(
                "rejected normalized allocation cannot realize PnL"
            )


@dataclass(frozen=True, slots=True)
class Phase19NormalizedCapitalSnapshot:
    observed_at: datetime
    realized_capital_ncu: Decimal
    reserved_risk_ncu: Decimal
    available_capital_ncu: Decimal
    peak_realized_capital_ncu: Decimal
    max_drawdown_ncu: Decimal
    capacity_breach: bool
    event: str
    signal_fingerprint: str

    def __post_init__(self) -> None:
        _aware(self.observed_at, name="observed_at")
        for name in (
            "realized_capital_ncu",
            "reserved_risk_ncu",
            "available_capital_ncu",
            "peak_realized_capital_ncu",
            "max_drawdown_ncu",
        ):
            _finite(getattr(self, name), name=name)
        if self.reserved_risk_ncu < 0 or self.available_capital_ncu < 0:
            raise CiboCapitalManagementError(
                "normalized reserved/available capital cannot be negative"
            )
        if self.peak_realized_capital_ncu < self.realized_capital_ncu:
            raise CiboCapitalManagementError(
                "normalized peak capital cannot trail realized capital"
            )
        if self.max_drawdown_ncu < 0:
            raise CiboCapitalManagementError(
                "normalized drawdown cannot be negative"
            )
        if type(self.capacity_breach) is not bool:
            raise CiboCapitalManagementError("capacity_breach must be bool")
        if not self.event or not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "normalized capital snapshot identity is required"
            )


@dataclass(frozen=True, slots=True)
class Phase19NormalizedCapitalReplay:
    contract: Phase19CapitalNumeraireContract
    initial_capital_ncu: Decimal
    ending_capital_ncu: Decimal
    total_realized_delta_ncu: Decimal
    max_drawdown_ncu: Decimal
    peak_reserved_risk_ncu: Decimal
    risk_capacity_minutes_ncu: Decimal
    accepted_opportunities: int
    rejected_opportunities: int
    capacity_breach_observed: bool
    decisions: tuple[Phase19NormalizedCapitalDecision, ...]
    snapshots: tuple[Phase19NormalizedCapitalSnapshot, ...]
    usd_arithmetic_performed: bool = False
    historical_provider_economics_claimed: bool = False
    cross_trader_raw_r_aggregation_performed: bool = False
    same_timestamp_exit_recycling_authorized: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _positive(self.initial_capital_ncu, name="initial_capital_ncu")
        for name in (
            "ending_capital_ncu",
            "total_realized_delta_ncu",
            "max_drawdown_ncu",
            "peak_reserved_risk_ncu",
            "risk_capacity_minutes_ncu",
        ):
            _finite(getattr(self, name), name=name)
        if self.max_drawdown_ncu < 0 or self.peak_reserved_risk_ncu < 0:
            raise CiboCapitalManagementError(
                "normalized replay risk metrics cannot be negative"
            )
        if self.risk_capacity_minutes_ncu < 0:
            raise CiboCapitalManagementError(
                "normalized risk-capacity minutes cannot be negative"
            )
        if self.accepted_opportunities < 0 or self.rejected_opportunities < 0:
            raise CiboCapitalManagementError(
                "normalized replay counts cannot be negative"
            )
        if (
            self.accepted_opportunities + self.rejected_opportunities
            != len(self.decisions)
        ):
            raise CiboCapitalManagementError(
                "normalized replay decision counts drift"
            )
        if self.ending_capital_ncu != (
            self.initial_capital_ncu + self.total_realized_delta_ncu
        ):
            raise CiboCapitalManagementError(
                "normalized replay capital accounting drift"
            )
        if (
            self.usd_arithmetic_performed
            or self.historical_provider_economics_claimed
            or self.cross_trader_raw_r_aggregation_performed
            or self.same_timestamp_exit_recycling_authorized
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase 19 normalized replay governance drift"
            )


def replay_phase19_normalized_capital(
    *,
    contract: Phase19CapitalNumeraireContract,
    initial_capital_ncu: Decimal,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> Phase19NormalizedCapitalReplay:
    """Replay a frozen normalized capital policy without provider economics.

    Entry events are processed before exit events at the same timestamp. This
    intentionally forbids assuming instantaneous same-timestamp settlement or
    recycling when historical provider settlement evidence is unavailable.
    """

    if not isinstance(contract, Phase19CapitalNumeraireContract):
        raise CiboCapitalManagementError(
            "normalized capital replay contract is invalid"
        )
    _positive(initial_capital_ncu, name="initial_capital_ncu")
    if not trades:
        raise CiboCapitalManagementError(
            "normalized capital replay requires trades"
        )

    fingerprints = tuple(
        item.opportunity.signal_fingerprint for item in trades
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "duplicate signal in normalized capital replay"
        )

    entry_events = {
        item.opportunity.signal_fingerprint: item for item in trades
    }
    accepted: dict[str, Phase19NormalizedReplayTrade] = {}
    decision_status: dict[str, Phase19NormalizedAllocationStatus] = {}
    realized_delta: dict[str, Decimal] = {}

    events: list[
        tuple[datetime, int, int, str, str]
    ] = []
    for item in trades:
        opportunity = item.opportunity
        allocation = item.allocation
        events.append(
            (
                opportunity.entry_at,
                0,
                allocation.allocation_priority,
                opportunity.trader_id.value,
                opportunity.signal_fingerprint,
            )
        )
        events.append(
            (
                opportunity.exit_at,
                1,
                0,
                opportunity.trader_id.value,
                opportunity.signal_fingerprint,
            )
        )
    events.sort()

    realized = initial_capital_ncu
    reserved = Decimal(0)
    peak = realized
    max_drawdown = Decimal(0)
    peak_reserved = Decimal(0)
    risk_capacity_minutes = Decimal(0)
    prior_at: datetime | None = None
    capacity_breach_observed = False
    snapshots: list[Phase19NormalizedCapitalSnapshot] = []

    for observed_at, event_kind, _priority, _trader_name, fingerprint in events:
        if prior_at is not None and observed_at > prior_at:
            minutes = Decimal(
                str((observed_at - prior_at).total_seconds())
            ) / Decimal(60)
            risk_capacity_minutes += reserved * minutes

        item = entry_events[fingerprint]
        allocation = item.allocation

        if event_kind == 0:
            available = max(Decimal(0), realized - reserved)
            if realized <= 0:
                status = (
                    Phase19NormalizedAllocationStatus.REJECTED_INSOLVENT_CAPITAL
                )
            elif allocation.risk_budget_ncu > available:
                status = (
                    Phase19NormalizedAllocationStatus.REJECTED_INSUFFICIENT_CAPACITY
                )
            else:
                status = Phase19NormalizedAllocationStatus.ACCEPTED
                reserved += allocation.risk_budget_ncu
                accepted[fingerprint] = item
            decision_status[fingerprint] = status
            event_name = f"ENTRY_{status.value}"
        else:
            if fingerprint not in accepted:
                prior_at = observed_at
                continue
            reserved -= allocation.risk_budget_ncu
            delta = allocation.risk_budget_ncu * item.normalized_outcome_r
            realized += delta
            realized_delta[fingerprint] = delta
            peak = max(peak, realized)
            max_drawdown = max(max_drawdown, peak - realized)
            event_name = "EXIT_SETTLED_NORMALIZED"

        available = max(Decimal(0), realized - reserved)
        breach = reserved > max(Decimal(0), realized)
        capacity_breach_observed = capacity_breach_observed or breach
        peak_reserved = max(peak_reserved, reserved)
        snapshots.append(
            Phase19NormalizedCapitalSnapshot(
                observed_at=observed_at,
                realized_capital_ncu=realized,
                reserved_risk_ncu=reserved,
                available_capital_ncu=available,
                peak_realized_capital_ncu=peak,
                max_drawdown_ncu=max_drawdown,
                capacity_breach=breach,
                event=event_name,
                signal_fingerprint=fingerprint,
            )
        )
        prior_at = observed_at

    decisions = tuple(
        Phase19NormalizedCapitalDecision(
            signal_fingerprint=item.opportunity.signal_fingerprint,
            trader_id=item.opportunity.trader_id,
            entry_at=item.opportunity.entry_at,
            exit_at=item.opportunity.exit_at,
            requested_risk_ncu=item.allocation.risk_budget_ncu,
            status=decision_status[item.opportunity.signal_fingerprint],
            realized_delta_ncu=realized_delta.get(
                item.opportunity.signal_fingerprint
            ),
        )
        for item in sorted(
            trades,
            key=lambda trade: (
                trade.opportunity.entry_at,
                trade.allocation.allocation_priority,
                trade.opportunity.trader_id.value,
                trade.opportunity.signal_fingerprint,
            ),
        )
    )
    accepted_count = sum(
        item.status is Phase19NormalizedAllocationStatus.ACCEPTED
        for item in decisions
    )
    total_delta = sum(
        (
            item.realized_delta_ncu
            for item in decisions
            if item.realized_delta_ncu is not None
        ),
        Decimal(0),
    )

    return Phase19NormalizedCapitalReplay(
        contract=contract,
        initial_capital_ncu=initial_capital_ncu,
        ending_capital_ncu=realized,
        total_realized_delta_ncu=total_delta,
        max_drawdown_ncu=max_drawdown,
        peak_reserved_risk_ncu=peak_reserved,
        risk_capacity_minutes_ncu=risk_capacity_minutes,
        accepted_opportunities=accepted_count,
        rejected_opportunities=len(decisions) - accepted_count,
        capacity_breach_observed=capacity_breach_observed,
        decisions=decisions,
        snapshots=tuple(snapshots),
    )
