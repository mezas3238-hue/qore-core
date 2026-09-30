from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_capital_collision import (
    compare_phase19_marginal_capacity,
    measure_phase19_capital_collisions,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
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
) -> Phase19NormalizedReplayTrade:
    entry_at = _at(entry_minute)
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol="TEST",
        entry_at=entry_at,
        exit_at=_at(exit_minute),
    )
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=signal,
        trader_id=trader,
        decision_at=entry_at - timedelta(seconds=1),
        risk_budget_ncu=Decimal(risk),
        allocation_priority=priority,
        policy_id="frozen-mechanics-v1",
        evidence_id=f"allocation:{signal}",
        train_cutoff_at=entry_at - timedelta(days=1),
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=Decimal(outcome),
        outcome_evidence_id=f"outcome:{signal}",
    )


def test_collision_requires_binding_capacity_with_active_blocker() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19g-test")
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="first",
            entry_minute=1,
            exit_minute=5,
            risk="0.7",
            outcome="0",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="second",
            entry_minute=2,
            exit_minute=4,
            risk="0.4",
            outcome="2",
        ),
    )
    replay = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=Decimal("1"),
        trades=trades,
    )

    evidence = measure_phase19_capital_collisions(
        replay=replay,
        trades=trades,
    )

    assert evidence.accepted_opportunities == 1
    assert evidence.rejected_insufficient_capacity == 1
    assert evidence.depletion_only_rejections == 0
    assert len(evidence.collisions) == 1

    collision = evidence.collisions[0]
    assert collision.signal_fingerprint == "second"
    assert collision.available_capital_ncu == Decimal("0.3")
    assert collision.capacity_shortfall_ncu == Decimal("0.1")
    assert len(collision.blockers) == 1
    assert collision.blockers[0].signal_fingerprint == "first"
    assert collision.cross_trader_blockers == 1
    assert evidence.allocation_authority is False


def test_realized_depletion_is_not_mislabeled_as_collision() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19g-test")
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="loss",
            entry_minute=1,
            exit_minute=2,
            risk="1",
            outcome="-0.8",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="later",
            entry_minute=3,
            exit_minute=4,
            risk="0.3",
            outcome="1",
        ),
    )
    replay = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=Decimal("1"),
        trades=trades,
    )

    evidence = measure_phase19_capital_collisions(
        replay=replay,
        trades=trades,
    )

    assert evidence.rejected_insufficient_capacity == 1
    assert evidence.depletion_only_rejections == 1
    assert evidence.collisions == ()


def test_same_timestamp_exit_remains_collision_blocker() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19g-test")
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="closing",
            entry_minute=1,
            exit_minute=3,
            risk="0.8",
            outcome="1",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="entering",
            entry_minute=3,
            exit_minute=4,
            risk="0.3",
            outcome="1",
        ),
    )
    replay = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=Decimal("1"),
        trades=trades,
    )

    evidence = measure_phase19_capital_collisions(
        replay=replay,
        trades=trades,
    )

    assert len(evidence.collisions) == 1
    assert evidence.collisions[0].blockers[0].signal_fingerprint == "closing"


def test_marginal_capacity_is_ex_post_delta_not_forecast() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19g-test")
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="first",
            entry_minute=1,
            exit_minute=5,
            risk="0.7",
            outcome="0",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="second",
            entry_minute=2,
            exit_minute=4,
            risk="0.4",
            outcome="2",
        ),
    )

    evidence = compare_phase19_marginal_capacity(
        contract=contract,
        lower_initial_capital_ncu=Decimal("1"),
        higher_initial_capital_ncu=Decimal("1.2"),
        trades=trades,
    )

    assert evidence.capacity_step_ncu == Decimal("0.2")
    assert evidence.lower_total_realized_delta_ncu == Decimal("0")
    assert evidence.higher_total_realized_delta_ncu == Decimal("0.8")
    assert evidence.marginal_realized_delta_ncu == Decimal("0.8")
    assert evidence.rejection_reduction == 1
    assert evidence.additional_accepted_opportunities == 1
    assert evidence.ex_post_only is True
    assert evidence.causal_forecast is False
    assert evidence.true_optimization_dual_claimed is False
    assert evidence.allocation_authority is False


def test_more_initial_capacity_can_have_negative_path_dependent_value() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19g-test")
    trades = (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            signal="anchor",
            entry_minute=1,
            exit_minute=5,
            risk="0.7",
            outcome="0",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            signal="extra-loss",
            entry_minute=2,
            exit_minute=3,
            risk="0.4",
            outcome="-2",
        ),
        _trade(
            trader=TraderLineage.R42_AUDJPY,
            signal="later-win",
            entry_minute=4,
            exit_minute=6,
            risk="0.4",
            outcome="3",
        ),
    )

    evidence = compare_phase19_marginal_capacity(
        contract=contract,
        lower_initial_capital_ncu=Decimal("1"),
        higher_initial_capital_ncu=Decimal("1.2"),
        trades=trades,
    )

    assert evidence.marginal_realized_delta_ncu < 0
