from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_capital_collision import (
    measure_phase19_capital_collisions,
)
from qore.infrastructure.cibo_ce2i_phase19_hypergraph import (
    Phase19HyperedgeKind,
    build_phase19_collision_hyperedges,
    build_phase19_opportunity_hypergraph,
    build_phase19_temporal_hyperedges,
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


def _opp(
    trader: TraderLineage,
    signal: str,
    entry: int,
    exit_: int,
) -> Phase19ChronologicalOpportunity:
    return Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol="TEST",
        entry_at=_at(entry),
        exit_at=_at(exit_),
    )


def _trade(
    trader: TraderLineage,
    signal: str,
    entry: int,
    exit_: int,
    risk: str,
    outcome: str,
) -> Phase19NormalizedReplayTrade:
    opportunity = _opp(trader, signal, entry, exit_)
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=signal,
        trader_id=trader,
        decision_at=opportunity.entry_at - timedelta(seconds=1),
        risk_budget_ncu=Decimal(risk),
        allocation_priority=0,
        policy_id="hypergraph-test-policy",
        evidence_id=f"allocation:{signal}",
        train_cutoff_at=opportunity.entry_at - timedelta(days=1),
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=Decimal(outcome),
        outcome_evidence_id=f"outcome:{signal}",
    )


def test_temporal_hypergraph_captures_multi_trader_concurrency() -> None:
    opportunities = (
        _opp(TraderLineage.R38_EURUSD, "a", 0, 10),
        _opp(TraderLineage.R43_GBPUSD, "b", 2, 8),
        _opp(TraderLineage.R42_AUDJPY, "c", 4, 6),
    )

    edges = build_phase19_temporal_hyperedges(opportunities)

    assert edges
    assert max(len(edge.members) for edge in edges) == 3
    triple = next(edge for edge in edges if len(edge.members) == 3)
    assert triple.interval_start == _at(4)
    assert triple.interval_end == _at(6)
    assert triple.distinct_trader_count == 3
    assert triple.duration_seconds == Decimal("120")
    assert triple.kind is Phase19HyperedgeKind.TEMPORAL_CONCURRENCY


def test_same_trader_overlap_alone_is_not_cross_trader_hyperedge() -> None:
    opportunities = (
        _opp(TraderLineage.R38_EURUSD, "a", 0, 10),
        _opp(TraderLineage.R38_EURUSD, "b", 2, 8),
    )

    assert build_phase19_temporal_hyperedges(opportunities) == ()


def test_collision_hyperedge_preserves_resource_semantics() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19h-test")
    trades = (
        _trade(
            TraderLineage.R38_EURUSD,
            "blocker",
            1,
            5,
            "0.7",
            "0",
        ),
        _trade(
            TraderLineage.R43_GBPUSD,
            "rejected",
            2,
            4,
            "0.4",
            "1",
        ),
    )
    replay = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=Decimal("1"),
        trades=trades,
    )
    collision = measure_phase19_capital_collisions(
        replay=replay,
        trades=trades,
    )

    edges = build_phase19_collision_hyperedges(
        evidence=collision,
        trades=trades,
    )

    assert len(edges) == 1
    edge = edges[0]
    assert edge.kind is Phase19HyperedgeKind.NORMALIZED_CAPITAL_COLLISION
    assert edge.rejected_member.signal_fingerprint == "rejected"
    assert edge.blocker_members[0].signal_fingerprint == "blocker"
    assert edge.cardinality == 2
    assert edge.distinct_trader_count == 2
    assert edge.capacity_shortfall_ncu == Decimal("0.1")


def test_combined_hypergraph_has_no_sizing_or_allocation_authority() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="phase19h-test")
    trades = (
        _trade(
            TraderLineage.R38_EURUSD,
            "a",
            1,
            5,
            "0.7",
            "0",
        ),
        _trade(
            TraderLineage.R43_GBPUSD,
            "b",
            2,
            4,
            "0.4",
            "1",
        ),
        _trade(
            TraderLineage.R42_AUDJPY,
            "c",
            2,
            3,
            "0.1",
            "1",
        ),
    )
    replay = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=Decimal("1"),
        trades=trades,
    )
    collision = measure_phase19_capital_collisions(
        replay=replay,
        trades=trades,
    )

    graph = build_phase19_opportunity_hypergraph(
        opportunities=tuple(item.opportunity for item in trades),
        collision_evidence=((collision, trades),),
    )

    assert graph.max_temporal_cardinality == 3
    assert graph.max_collision_cardinality >= 2
    assert graph.temporal_evidence_only is True
    assert graph.collision_evidence_ex_post_only is True
    assert graph.harmful_dependence_claimed is False
    assert graph.sizing_penalty_authorized is False
    assert graph.allocation_authority is False
    assert graph.risk_authority is False
    assert graph.execution_authority is False
