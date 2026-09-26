"""Phase 19G normalized capital-collision and marginal-capacity evidence.

A temporal overlap becomes a *capital collision* only when a frozen normalized
capital policy rejects an opportunity for insufficient capacity while one or
more previously accepted opportunities still reserve capacity.

This module also computes a finite-difference marginal-capacity diagnostic by
replaying the *same frozen policy* at two predeclared normalized-capital levels.
The resulting delta is post-trade evaluation evidence only. It is not a causal
expected value, not a true optimization dual variable, and cannot influence
sizing/allocation/Risk/execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedAllocationStatus,
    Phase19NormalizedCapitalDecision,
    Phase19NormalizedCapitalReplay,
    Phase19NormalizedReplayTrade,
    replay_phase19_normalized_capital,
)


def _finite(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite Decimal")


def _positive(value: Decimal, *, name: str) -> None:
    _finite(value, name=name)
    if value <= 0:
        raise CiboCapitalManagementError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class Phase19CollisionBlocker:
    signal_fingerprint: str
    trader_id: TraderLineage
    reserved_risk_ncu: Decimal

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "collision blocker signal identity is required"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "collision blocker Trader identity is invalid"
            )
        _positive(self.reserved_risk_ncu, name="reserved_risk_ncu")


@dataclass(frozen=True, slots=True)
class Phase19CapitalCollision:
    signal_fingerprint: str
    trader_id: TraderLineage
    requested_risk_ncu: Decimal
    available_capital_ncu: Decimal
    capacity_shortfall_ncu: Decimal
    blockers: tuple[Phase19CollisionBlocker, ...]
    cross_trader_blockers: int

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "capital collision signal identity is required"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "capital collision Trader identity is invalid"
            )
        _positive(self.requested_risk_ncu, name="requested_risk_ncu")
        _finite(self.available_capital_ncu, name="available_capital_ncu")
        _positive(self.capacity_shortfall_ncu, name="capacity_shortfall_ncu")
        if self.available_capital_ncu < 0:
            raise CiboCapitalManagementError(
                "capital collision available capacity cannot be negative"
            )
        if not self.blockers:
            raise CiboCapitalManagementError(
                "capital collision requires at least one active blocker"
            )
        if (
            type(self.cross_trader_blockers) is not int
            or self.cross_trader_blockers < 0
            or self.cross_trader_blockers > len(self.blockers)
        ):
            raise CiboCapitalManagementError(
                "capital collision cross-Trader blocker count is invalid"
            )


@dataclass(frozen=True, slots=True)
class Phase19CapitalCollisionEvidence:
    initial_capital_ncu: Decimal
    accepted_opportunities: int
    rejected_insufficient_capacity: int
    rejected_insolvent_capital: int
    collisions: tuple[Phase19CapitalCollision, ...]
    depletion_only_rejections: int
    ex_post_outcomes_used: bool = True
    descriptive_only: bool = True
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _positive(self.initial_capital_ncu, name="initial_capital_ncu")
        for name in (
            "accepted_opportunities",
            "rejected_insufficient_capacity",
            "rejected_insolvent_capital",
            "depletion_only_rejections",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCapitalManagementError(
                    f"{name} must be non-negative int"
                )
        if len(self.collisions) > self.rejected_insufficient_capacity:
            raise CiboCapitalManagementError(
                "capital collisions cannot exceed insufficient-capacity rejections"
            )
        if (
            len(self.collisions) + self.depletion_only_rejections
            != self.rejected_insufficient_capacity
        ):
            raise CiboCapitalManagementError(
                "insufficient-capacity rejection classification drift"
            )
        if not self.ex_post_outcomes_used or not self.descriptive_only:
            raise CiboCapitalManagementError(
                "capital collision evidence semantics drift"
            )
        if self.allocation_authority or self.risk_authority or self.execution_authority:
            raise CiboCapitalManagementError(
                "capital collision evidence cannot carry trading authority"
            )


@dataclass(frozen=True, slots=True)
class Phase19MarginalCapacityEvidence:
    lower_initial_capital_ncu: Decimal
    higher_initial_capital_ncu: Decimal
    capacity_step_ncu: Decimal
    lower_total_realized_delta_ncu: Decimal
    higher_total_realized_delta_ncu: Decimal
    marginal_realized_delta_ncu: Decimal
    lower_rejected_opportunities: int
    higher_rejected_opportunities: int
    rejection_reduction: int
    additional_accepted_opportunities: int
    ex_post_only: bool = True
    causal_forecast: bool = False
    true_optimization_dual_claimed: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "lower_initial_capital_ncu",
            "higher_initial_capital_ncu",
            "capacity_step_ncu",
        ):
            _positive(getattr(self, name), name=name)
        if (
            self.higher_initial_capital_ncu
            <= self.lower_initial_capital_ncu
        ):
            raise CiboCapitalManagementError(
                "higher normalized capacity must exceed lower capacity"
            )
        if self.capacity_step_ncu != (
            self.higher_initial_capital_ncu
            - self.lower_initial_capital_ncu
        ):
            raise CiboCapitalManagementError(
                "marginal capacity step accounting drift"
            )
        for name in (
            "lower_total_realized_delta_ncu",
            "higher_total_realized_delta_ncu",
            "marginal_realized_delta_ncu",
        ):
            _finite(getattr(self, name), name=name)
        if self.marginal_realized_delta_ncu != (
            self.higher_total_realized_delta_ncu
            - self.lower_total_realized_delta_ncu
        ):
            raise CiboCapitalManagementError(
                "marginal realized delta accounting drift"
            )
        for name in (
            "lower_rejected_opportunities",
            "higher_rejected_opportunities",
            "rejection_reduction",
            "additional_accepted_opportunities",
        ):
            value = getattr(self, name)
            if type(value) is not int:
                raise CiboCapitalManagementError(
                    f"{name} must be int"
                )
        if self.rejection_reduction != (
            self.lower_rejected_opportunities
            - self.higher_rejected_opportunities
        ):
            raise CiboCapitalManagementError(
                "marginal rejection accounting drift"
            )
        if self.additional_accepted_opportunities < 0:
            raise CiboCapitalManagementError(
                "higher capacity cannot report negative additional accepts"
            )
        if (
            not self.ex_post_only
            or self.causal_forecast
            or self.true_optimization_dual_claimed
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "marginal capacity evidence governance drift"
            )


def _decision_by_signal(
    replay: Phase19NormalizedCapitalReplay,
) -> dict[str, Phase19NormalizedCapitalDecision]:
    return {
        item.signal_fingerprint: item for item in replay.decisions
    }


def measure_phase19_capital_collisions(
    *,
    replay: Phase19NormalizedCapitalReplay,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> Phase19CapitalCollisionEvidence:
    """Classify actual scarcity under one frozen normalized-capital replay."""

    if not isinstance(replay, Phase19NormalizedCapitalReplay):
        raise CiboCapitalManagementError(
            "capital collision replay must be Phase19NormalizedCapitalReplay"
        )
    if not trades:
        raise CiboCapitalManagementError(
            "capital collision evidence requires trades"
        )
    by_signal = {
        item.opportunity.signal_fingerprint: item for item in trades
    }
    if len(by_signal) != len(trades):
        raise CiboCapitalManagementError(
            "duplicate signal in capital collision trades"
        )
    decisions = _decision_by_signal(replay)
    if set(decisions) != set(by_signal):
        raise CiboCapitalManagementError(
            "capital collision trade/replay population mismatch"
        )

    accepted_signals = {
        signal
        for signal, decision in decisions.items()
        if decision.status is Phase19NormalizedAllocationStatus.ACCEPTED
    }
    insufficient = 0
    insolvent = 0
    depletion_only = 0
    collisions: list[Phase19CapitalCollision] = []

    snapshot_by_signal = {
        item.signal_fingerprint: item
        for item in replay.snapshots
        if item.event.startswith("ENTRY_")
    }

    for signal, decision in decisions.items():
        if (
            decision.status
            is Phase19NormalizedAllocationStatus.REJECTED_INSOLVENT_CAPITAL
        ):
            insolvent += 1
            continue
        if (
            decision.status
            is not Phase19NormalizedAllocationStatus.REJECTED_INSUFFICIENT_CAPACITY
        ):
            continue

        insufficient += 1
        trade = by_signal[signal]
        entry_at = trade.opportunity.entry_at
        blockers: list[Phase19CollisionBlocker] = []
        for active_signal in accepted_signals:
            active = by_signal[active_signal]
            if active.opportunity.entry_at > entry_at:
                continue
            if active.opportunity.exit_at < entry_at:
                continue
            # For equal timestamps, only entries ordered before the rejected
            # signal may have consumed capacity.
            if active.opportunity.entry_at == entry_at:
                active_key = (
                    active.allocation.allocation_priority,
                    active.opportunity.trader_id.value,
                    active_signal,
                )
                rejected_key = (
                    trade.allocation.allocation_priority,
                    trade.opportunity.trader_id.value,
                    signal,
                )
                if active_key >= rejected_key:
                    continue
            blockers.append(
                Phase19CollisionBlocker(
                    signal_fingerprint=active_signal,
                    trader_id=active.opportunity.trader_id,
                    reserved_risk_ncu=active.allocation.risk_budget_ncu,
                )
            )

        if not blockers:
            depletion_only += 1
            continue

        snapshot = snapshot_by_signal.get(signal)
        if snapshot is None:
            raise CiboCapitalManagementError(
                "capital collision rejection snapshot missing"
            )
        shortfall = (
            decision.requested_risk_ncu - snapshot.available_capital_ncu
        )
        if shortfall <= 0:
            raise CiboCapitalManagementError(
                "capital collision rejection has no positive shortfall"
            )
        blockers_tuple = tuple(
            sorted(
                blockers,
                key=lambda item: (
                    item.trader_id.value,
                    item.signal_fingerprint,
                ),
            )
        )
        collisions.append(
            Phase19CapitalCollision(
                signal_fingerprint=signal,
                trader_id=decision.trader_id,
                requested_risk_ncu=decision.requested_risk_ncu,
                available_capital_ncu=snapshot.available_capital_ncu,
                capacity_shortfall_ncu=shortfall,
                blockers=blockers_tuple,
                cross_trader_blockers=sum(
                    blocker.trader_id is not decision.trader_id
                    for blocker in blockers_tuple
                ),
            )
        )

    accepted_count = sum(
        decision.status is Phase19NormalizedAllocationStatus.ACCEPTED
        for decision in decisions.values()
    )
    return Phase19CapitalCollisionEvidence(
        initial_capital_ncu=replay.initial_capital_ncu,
        accepted_opportunities=accepted_count,
        rejected_insufficient_capacity=insufficient,
        rejected_insolvent_capital=insolvent,
        collisions=tuple(
            sorted(
                collisions,
                key=lambda item: (
                    by_signal[item.signal_fingerprint].opportunity.entry_at,
                    item.trader_id.value,
                    item.signal_fingerprint,
                ),
            )
        ),
        depletion_only_rejections=depletion_only,
    )


def compare_phase19_marginal_capacity(
    *,
    contract: Phase19CapitalNumeraireContract,
    lower_initial_capital_ncu: Decimal,
    higher_initial_capital_ncu: Decimal,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> Phase19MarginalCapacityEvidence:
    """Finite-difference ex-post value of extra normalized capacity."""

    _positive(lower_initial_capital_ncu, name="lower_initial_capital_ncu")
    _positive(higher_initial_capital_ncu, name="higher_initial_capital_ncu")
    if higher_initial_capital_ncu <= lower_initial_capital_ncu:
        raise CiboCapitalManagementError(
            "higher normalized capacity must exceed lower capacity"
        )

    lower = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=lower_initial_capital_ncu,
        trades=trades,
    )
    higher = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=higher_initial_capital_ncu,
        trades=trades,
    )
    return Phase19MarginalCapacityEvidence(
        lower_initial_capital_ncu=lower_initial_capital_ncu,
        higher_initial_capital_ncu=higher_initial_capital_ncu,
        capacity_step_ncu=(
            higher_initial_capital_ncu - lower_initial_capital_ncu
        ),
        lower_total_realized_delta_ncu=lower.total_realized_delta_ncu,
        higher_total_realized_delta_ncu=higher.total_realized_delta_ncu,
        marginal_realized_delta_ncu=(
            higher.total_realized_delta_ncu
            - lower.total_realized_delta_ncu
        ),
        lower_rejected_opportunities=lower.rejected_opportunities,
        higher_rejected_opportunities=higher.rejected_opportunities,
        rejection_reduction=(
            lower.rejected_opportunities - higher.rejected_opportunities
        ),
        additional_accepted_opportunities=(
            higher.accepted_opportunities - lower.accepted_opportunities
        ),
    )
