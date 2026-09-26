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
    replay_phase19_normalized_capital,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)


def _at(minute: int) -> datetime:
    return datetime(2022, 1, 3, 12, minute, tzinfo=UTC)


def _trade(
    *,
    trader: TraderLineage,
    signal: str,
    entry_minute: int,
    exit_minute: int,
    risk: str,
    outcome: str,
    priority: int = 0,
    decision_minute: int | None = None,
) -> Phase19NormalizedReplayTrade:
    entry_at = _at(entry_minute)
    exit_at = _at(exit_minute)
    decision_at = (
        _at(decision_minute)
        if decision_minute is not None
        else entry_at - timedelta(seconds=1)
    )
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol="EURUSD",
        entry_at=entry_at,
        exit_at=exit_at,
    )
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=signal,
        trader_id=trader,
        decision_at=decision_at,
        risk_budget_ncu=Decimal(risk),
        allocation_priority=priority,
        policy_id="frozen-policy-v1",
        evidence_id=f"train:{signal}",
        train_cutoff_at=decision_at - timedelta(days=1),
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=Decimal(outcome),
        outcome_evidence_id=f"outcome:{signal}",
    )


def test_numeraire_forbids_usd_provider_and_raw_r_claims() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19c-v1")
    assert contract.provider_economics_required is False
    assert contract.usd_equivalence_claimed is False
    assert contract.cross_trader_raw_r_aggregation_authorized is False

    with pytest.raises(CiboCapitalManagementError, match="cannot claim"):
        Phase19CapitalNumeraireContract(
            contract_id="bad",
            usd_equivalence_claimed=True,
        )


def test_allocation_is_causal_and_cannot_be_outcome_aware() -> None:
    decision_at = _at(1)

    with pytest.raises(CiboCapitalManagementError, match="outcome-aware"):
        Phase19NormalizedCapitalAllocation(
            signal_fingerprint="s",
            trader_id=TraderLineage.R38_EURUSD,
            decision_at=decision_at,
            risk_budget_ncu=Decimal("0.1"),
            allocation_priority=0,
            policy_id="policy",
            evidence_id="evidence",
            outcome_aware=True,
        )

    with pytest.raises(CiboCapitalManagementError, match="train cutoff"):
        Phase19NormalizedCapitalAllocation(
            signal_fingerprint="s",
            trader_id=TraderLineage.R38_EURUSD,
            decision_at=decision_at,
            risk_budget_ncu=Decimal("0.1"),
            allocation_priority=0,
            policy_id="policy",
            evidence_id="evidence",
            train_cutoff_at=decision_at + timedelta(seconds=1),
        )


def test_trade_rejects_decision_after_entry() -> None:
    with pytest.raises(CiboCapitalManagementError, match="after entry"):
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="late",
            entry_minute=1,
            exit_minute=2,
            risk="0.1",
            outcome="1",
            decision_minute=2,
        )


def test_normalized_replay_uses_budget_weighted_outcome_not_raw_r_sum() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19c-v1")
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="a",
            entry_minute=1,
            exit_minute=2,
            risk="0.10",
            outcome="2",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="b",
            entry_minute=3,
            exit_minute=4,
            risk="0.20",
            outcome="-0.5",
        ),
    )

    result = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=Decimal("1"),
        trades=trades,
    )

    assert result.accepted_opportunities == 2
    assert result.rejected_opportunities == 0
    assert result.total_realized_delta_ncu == Decimal("0.10")
    assert result.ending_capital_ncu == Decimal("1.10")
    assert result.usd_arithmetic_performed is False
    assert result.cross_trader_raw_r_aggregation_performed is False


def test_insufficient_capacity_rejects_without_clipping_budget() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19c-v1")
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="first",
            entry_minute=1,
            exit_minute=4,
            risk="0.70",
            outcome="0",
            priority=0,
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="second",
            entry_minute=2,
            exit_minute=3,
            risk="0.40",
            outcome="10",
            priority=0,
        ),
    )

    result = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=Decimal("1"),
        trades=trades,
    )

    by_signal = {item.signal_fingerprint: item for item in result.decisions}
    assert (
        by_signal["second"].status
        is Phase19NormalizedAllocationStatus.REJECTED_INSUFFICIENT_CAPACITY
    )
    assert by_signal["second"].requested_risk_ncu == Decimal("0.40")
    assert by_signal["second"].realized_delta_ncu is None
    assert result.total_realized_delta_ncu == Decimal("0")


def test_same_timestamp_exit_does_not_create_unproven_recycling() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19c-v1")
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="closing",
            entry_minute=1,
            exit_minute=3,
            risk="0.80",
            outcome="1",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="entering",
            entry_minute=3,
            exit_minute=4,
            risk="0.30",
            outcome="1",
        ),
    )

    result = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=Decimal("1"),
        trades=trades,
    )

    by_signal = {item.signal_fingerprint: item for item in result.decisions}
    assert (
        by_signal["entering"].status
        is Phase19NormalizedAllocationStatus.REJECTED_INSUFFICIENT_CAPACITY
    )
    assert result.same_timestamp_exit_recycling_authorized is False
    assert result.ending_capital_ncu == Decimal("1.80")


def test_large_loss_can_reveal_capacity_breach_without_hidden_recapitalization() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19c-v1")
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="loss",
            entry_minute=1,
            exit_minute=3,
            risk="0.40",
            outcome="-3",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="open",
            entry_minute=2,
            exit_minute=4,
            risk="0.40",
            outcome="0",
        ),
    )

    result = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=Decimal("1"),
        trades=trades,
    )

    assert result.capacity_breach_observed is True
    assert result.ending_capital_ncu == Decimal("-0.20")
    assert result.total_realized_delta_ncu == Decimal("-1.20")
    assert any(item.capacity_breach for item in result.snapshots)


def test_duplicate_signal_fails_closed() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19c-v1")
    trade = _trade(
        trader=TraderLineage.R38_EURUSD,
        signal="dup",
        entry_minute=1,
        exit_minute=2,
        risk="0.10",
        outcome="1",
    )

    with pytest.raises(CiboCapitalManagementError, match="duplicate signal"):
        replay_phase19_normalized_capital(
            contract=contract,
            initial_capital_ncu=Decimal("1"),
            trades=(trade, trade),
        )
