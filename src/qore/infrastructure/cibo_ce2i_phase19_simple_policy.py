"""Phase 19I transparent normalized-capital policy baseline contracts.

These contracts deliberately stay below optimizer complexity. A policy may only
choose a fixed normalized risk budget and optionally hold a fixed amount of the
initial normalized capital outside the deployable pool.

The policy builder consumes pre-trade opportunity/allocation fields only. It
cannot inspect outcome, future overlap, validation results, provider economics,
USD PnL, QORE Risk decisions, or broker execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedCapitalReplay,
    Phase19NormalizedReplayTrade,
    replay_phase19_normalized_capital,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)


def _finite(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite Decimal")


@dataclass(frozen=True, slots=True)
class Phase19SimpleCapitalPolicy:
    """One low-dimensional policy declared before empirical evaluation."""

    policy_id: str
    gross_initial_capital_ncu: Decimal
    fixed_reserve_ncu: Decimal
    risk_budget_ncu: Decimal
    allocation_priority: int = 0
    outcome_aware: bool = False
    validation_tuned: bool = False
    advanced_optimizer: bool = False
    trader_specific_weighting: bool = False
    overlap_penalty: bool = False
    hypergraph_penalty: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise CiboCapitalManagementError(
                "simple capital policy identity is required"
            )
        for name in (
            "gross_initial_capital_ncu",
            "fixed_reserve_ncu",
            "risk_budget_ncu",
        ):
            _finite(getattr(self, name), name=name)
        if self.gross_initial_capital_ncu <= 0:
            raise CiboCapitalManagementError(
                "gross initial normalized capital must be positive"
            )
        if self.fixed_reserve_ncu < 0:
            raise CiboCapitalManagementError(
                "fixed normalized reserve cannot be negative"
            )
        if self.fixed_reserve_ncu >= self.gross_initial_capital_ncu:
            raise CiboCapitalManagementError(
                "fixed reserve must leave positive deployable capital"
            )
        if self.risk_budget_ncu <= 0:
            raise CiboCapitalManagementError(
                "simple policy risk budget must be positive"
            )
        if type(self.allocation_priority) is not int:
            raise CiboCapitalManagementError(
                "simple policy allocation priority must be int"
            )
        if self.allocation_priority < 0:
            raise CiboCapitalManagementError(
                "simple policy allocation priority cannot be negative"
            )
        if (
            self.outcome_aware
            or self.validation_tuned
            or self.advanced_optimizer
            or self.trader_specific_weighting
            or self.overlap_penalty
            or self.hypergraph_penalty
        ):
            raise CiboCapitalManagementError(
                "Phase 19I simple policy governance drift"
            )

    @property
    def deployable_initial_capital_ncu(self) -> Decimal:
        return self.gross_initial_capital_ncu - self.fixed_reserve_ncu


@dataclass(frozen=True, slots=True)
class Phase19SimplePolicyReplay:
    """Normalized replay plus capital held outside the deployable pool."""

    policy: Phase19SimpleCapitalPolicy
    replay: Phase19NormalizedCapitalReplay

    def __post_init__(self) -> None:
        if (
            self.replay.initial_capital_ncu
            != self.policy.deployable_initial_capital_ncu
        ):
            raise CiboCapitalManagementError(
                "simple policy deployable-capital binding drift"
            )
        if self.total_ending_capital_ncu != (
            self.policy.gross_initial_capital_ncu
            + self.replay.total_realized_delta_ncu
        ):
            raise CiboCapitalManagementError(
                "simple policy total-capital accounting drift"
            )

    @property
    def total_ending_capital_ncu(self) -> Decimal:
        return self.policy.fixed_reserve_ncu + self.replay.ending_capital_ncu


def build_phase19_simple_policy_allocation(
    *,
    policy: Phase19SimpleCapitalPolicy,
    opportunity: Phase19ChronologicalOpportunity,
    source_allocation: Phase19NormalizedCapitalAllocation,
) -> Phase19NormalizedCapitalAllocation:
    """Build an allocation without receiving post-trade outcome."""

    if opportunity.signal_fingerprint != source_allocation.signal_fingerprint:
        raise CiboCapitalManagementError(
            "simple policy source allocation signal mismatch"
        )
    if opportunity.trader_id is not source_allocation.trader_id:
        raise CiboCapitalManagementError(
            "simple policy source allocation Trader mismatch"
        )
    return Phase19NormalizedCapitalAllocation(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id,
        decision_at=source_allocation.decision_at,
        risk_budget_ncu=policy.risk_budget_ncu,
        allocation_priority=policy.allocation_priority,
        policy_id=policy.policy_id,
        evidence_id=(
            f"phase19i:{policy.policy_id}:{source_allocation.evidence_id}"
        ),
        train_cutoff_at=source_allocation.train_cutoff_at,
        outcome_aware=False,
    )


def replay_phase19_simple_policy(
    *,
    policy: Phase19SimpleCapitalPolicy,
    contract: Phase19CapitalNumeraireContract,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> Phase19SimplePolicyReplay:
    """Replay one frozen policy using the existing normalized capital ledger."""

    if not trades:
        raise CiboCapitalManagementError(
            "simple policy replay requires normalized trades"
        )
    transformed = tuple(
        Phase19NormalizedReplayTrade(
            opportunity=item.opportunity,
            allocation=build_phase19_simple_policy_allocation(
                policy=policy,
                opportunity=item.opportunity,
                source_allocation=item.allocation,
            ),
            normalized_outcome_r=item.normalized_outcome_r,
            outcome_evidence_id=item.outcome_evidence_id,
        )
        for item in trades
    )
    replay = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=policy.deployable_initial_capital_ncu,
        trades=transformed,
    )
    return Phase19SimplePolicyReplay(policy=policy, replay=replay)


PHASE19I_SIMPLE_POLICIES = (
    Phase19SimpleCapitalPolicy(
        policy_id="P19I_EQUAL_100_NO_RESERVE",
        gross_initial_capital_ncu=Decimal("10"),
        fixed_reserve_ncu=Decimal("0"),
        risk_budget_ncu=Decimal("1"),
    ),
    Phase19SimpleCapitalPolicy(
        policy_id="P19I_EQUAL_075_NO_RESERVE",
        gross_initial_capital_ncu=Decimal("10"),
        fixed_reserve_ncu=Decimal("0"),
        risk_budget_ncu=Decimal("0.75"),
    ),
    Phase19SimpleCapitalPolicy(
        policy_id="P19I_EQUAL_050_NO_RESERVE",
        gross_initial_capital_ncu=Decimal("10"),
        fixed_reserve_ncu=Decimal("0"),
        risk_budget_ncu=Decimal("0.50"),
    ),
    Phase19SimpleCapitalPolicy(
        policy_id="P19I_EQUAL_025_NO_RESERVE",
        gross_initial_capital_ncu=Decimal("10"),
        fixed_reserve_ncu=Decimal("0"),
        risk_budget_ncu=Decimal("0.25"),
    ),
    Phase19SimpleCapitalPolicy(
        policy_id="P19I_EQUAL_050_RESERVE_2",
        gross_initial_capital_ncu=Decimal("10"),
        fixed_reserve_ncu=Decimal("2"),
        risk_budget_ncu=Decimal("0.50"),
    ),
    Phase19SimpleCapitalPolicy(
        policy_id="P19I_EQUAL_025_RESERVE_2",
        gross_initial_capital_ncu=Decimal("10"),
        fixed_reserve_ncu=Decimal("2"),
        risk_budget_ncu=Decimal("0.25"),
    ),
)
