from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedAllocationStatus,
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase19_simple_policy import (
    PHASE19I_SIMPLE_POLICIES,
    Phase19SimpleCapitalPolicy,
    build_phase19_simple_policy_allocation,
    replay_phase19_simple_policy,
)


def _trade(
    *,
    trader: TraderLineage,
    signal: str,
    entry_minute: int,
    exit_minute: int,
    outcome: str,
) -> Phase19NormalizedReplayTrade:
    entry_at = datetime(2022, 1, 3, 12, entry_minute, tzinfo=UTC)
    exit_at = datetime(2022, 1, 3, 12, exit_minute, tzinfo=UTC)
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol=trader.value,
        entry_at=entry_at,
        exit_at=exit_at,
    )
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=signal,
        trader_id=trader,
        decision_at=entry_at - timedelta(seconds=1),
        risk_budget_ncu=Decimal("1"),
        allocation_priority=0,
        policy_id="source",
        evidence_id=f"source:{signal}",
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=Decimal(outcome),
        outcome_evidence_id=f"outcome:{signal}",
    )


def test_simple_policy_rejects_noncausal_or_optimizer_features() -> None:
    with pytest.raises(CiboCapitalManagementError, match="governance drift"):
        Phase19SimpleCapitalPolicy(
            policy_id="bad",
            gross_initial_capital_ncu=Decimal("10"),
            fixed_reserve_ncu=Decimal("0"),
            risk_budget_ncu=Decimal("1"),
            overlap_penalty=True,
        )

    with pytest.raises(CiboCapitalManagementError, match="positive deployable"):
        Phase19SimpleCapitalPolicy(
            policy_id="bad-reserve",
            gross_initial_capital_ncu=Decimal("10"),
            fixed_reserve_ncu=Decimal("10"),
            risk_budget_ncu=Decimal("1"),
        )


def test_policy_builder_consumes_only_pretrade_contract_fields() -> None:
    trade = _trade(
        trader=TraderLineage.R38_EURUSD,
        signal="a",
        entry_minute=1,
        exit_minute=2,
        outcome="9",
    )
    policy = PHASE19I_SIMPLE_POLICIES[2]

    allocation = build_phase19_simple_policy_allocation(
        policy=policy,
        opportunity=trade.opportunity,
        source_allocation=trade.allocation,
    )

    assert allocation.risk_budget_ncu == Decimal("0.50")
    assert allocation.decision_at == trade.allocation.decision_at
    assert allocation.trader_id is TraderLineage.R38_EURUSD
    assert allocation.policy_id == policy.policy_id
    assert allocation.outcome_aware is False


def test_fixed_reserve_stays_outside_deployable_capital() -> None:
    policy = Phase19SimpleCapitalPolicy(
        policy_id="reserve-test",
        gross_initial_capital_ncu=Decimal("1"),
        fixed_reserve_ncu=Decimal("0.25"),
        risk_budget_ncu=Decimal("0.75"),
    )
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="first",
            entry_minute=1,
            exit_minute=4,
            outcome="1",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="second",
            entry_minute=2,
            exit_minute=3,
            outcome="10",
        ),
    )

    result = replay_phase19_simple_policy(
        policy=policy,
        contract=Phase19CapitalNumeraireContract(contract_id="test"),
        trades=trades,
    )

    decisions = {
        item.signal_fingerprint: item for item in result.replay.decisions
    }
    assert (
        decisions["second"].status
        is Phase19NormalizedAllocationStatus.REJECTED_INSUFFICIENT_CAPACITY
    )
    assert result.replay.initial_capital_ncu == Decimal("0.75")
    assert result.total_ending_capital_ncu == Decimal("1.75")
    assert result.replay.total_realized_delta_ncu == Decimal("0.75")


def test_frozen_phase19i_suite_is_small_equal_weight_and_unique() -> None:
    assert len(PHASE19I_SIMPLE_POLICIES) == 6
    assert len({item.policy_id for item in PHASE19I_SIMPLE_POLICIES}) == 6
    assert all(
        item.gross_initial_capital_ncu == Decimal("10")
        for item in PHASE19I_SIMPLE_POLICIES
    )
    assert all(
        item.trader_specific_weighting is False
        for item in PHASE19I_SIMPLE_POLICIES
    )
    assert all(
        item.overlap_penalty is False for item in PHASE19I_SIMPLE_POLICIES
    )
    assert all(
        item.hypergraph_penalty is False for item in PHASE19I_SIMPLE_POLICIES
    )
