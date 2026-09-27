from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase20_capital_state_monte_carlo import (
    build_phase20e_temporal_blocks,
    run_phase20e_capital_state_monte_carlo,
    sample_phase20e_block_path,
)


def _trade(
    *,
    trader: TraderLineage,
    fingerprint: str,
    decision_minute: int,
    entry_minute: int,
    exit_minute: int,
    outcome_r: str,
) -> Phase19NormalizedReplayTrade:
    base = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    decision_at = base.replace(
        hour=9 + decision_minute // 60,
        minute=decision_minute % 60,
    )
    entry_at = base.replace(
        hour=9 + entry_minute // 60,
        minute=entry_minute % 60,
    )
    exit_at = base.replace(
        hour=9 + exit_minute // 60,
        minute=exit_minute % 60,
    )
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=fingerprint,
        qore_symbol="EURUSD",
        entry_at=entry_at,
        exit_at=exit_at,
    )
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        decision_at=decision_at,
        risk_budget_ncu=Decimal("1"),
        allocation_priority=0,
        policy_id="SYNTHETIC_MC_POLICY",
        evidence_id=f"synthetic:{fingerprint}",
        outcome_aware=False,
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=Decimal(outcome_r),
        outcome_evidence_id=f"synthetic-outcome:{fingerprint}",
    )


def _population() -> tuple[Phase19NormalizedReplayTrade, ...]:
    return (
        _trade(
            trader=TraderLineage.R38_EURUSD,
            fingerprint="A",
            decision_minute=59,
            entry_minute=60,
            exit_minute=90,
            outcome_r="-1",
        ),
        _trade(
            trader=TraderLineage.R43_GBPUSD,
            fingerprint="B",
            decision_minute=64,
            entry_minute=65,
            exit_minute=80,
            outcome_r="-1",
        ),
        _trade(
            trader=TraderLineage.R38_GBPJPY,
            fingerprint="C",
            decision_minute=119,
            entry_minute=120,
            exit_minute=150,
            outcome_r="2",
        ),
        _trade(
            trader=TraderLineage.R42_AUDJPY,
            fingerprint="D",
            decision_minute=149,
            entry_minute=150,
            exit_minute=165,
            outcome_r="-1",
        ),
        _trade(
            trader=TraderLineage.VT31_NAS100,
            fingerprint="E",
            decision_minute=239,
            entry_minute=240,
            exit_minute=250,
            outcome_r="1",
        ),
    )


def test_phase20e_temporal_blocks_preserve_overlap_and_same_timestamp_capacity() -> None:
    blocks = build_phase20e_temporal_blocks(
        trades=_population(),
        components_per_block=1,
    )

    assert len(blocks) == 3
    assert [block.opportunity_count for block in blocks] == [2, 2, 1]
    assert {
        item.opportunity.signal_fingerprint for item in blocks[0].trades
    } == {"A", "B"}
    assert {
        item.opportunity.signal_fingerprint for item in blocks[1].trades
    } == {"C", "D"}


def test_phase20e_sampling_with_replacement_has_unique_identity_and_is_deterministic() -> None:
    blocks = build_phase20e_temporal_blocks(
        trades=_population(),
        components_per_block=1,
    )
    left = sample_phase20e_block_path(
        blocks=blocks,
        draws_per_path=6,
        seed=20020,
        simulation_id="MC_TEST",
    )
    right = sample_phase20e_block_path(
        blocks=blocks,
        draws_per_path=6,
        seed=20020,
        simulation_id="MC_TEST",
    )

    assert left.sampled_block_ids == right.sampled_block_ids
    assert tuple(
        item.opportunity.entry_at for item in left.trades
    ) == tuple(item.opportunity.entry_at for item in right.trades)
    fingerprints = tuple(
        item.opportunity.signal_fingerprint for item in left.trades
    )
    assert len(fingerprints) == len(set(fingerprints))
    assert left.independent_trade_shuffle is False
    assert left.market_probability_claimed is False
    assert left.policy_certified is False


def test_phase20e_sampled_blocks_do_not_overlap_each_other() -> None:
    blocks = build_phase20e_temporal_blocks(
        trades=_population(),
        components_per_block=1,
    )
    path = sample_phase20e_block_path(
        blocks=blocks,
        draws_per_path=8,
        seed=20021,
        simulation_id="MC_NON_OVERLAP",
    )

    draw_ranges: dict[int, tuple[datetime, datetime]] = {}
    for item in path.trades:
        parts = item.opportunity.signal_fingerprint.split(":")
        draw_index = int(parts[2])
        current = draw_ranges.get(draw_index)
        start = item.allocation.decision_at
        end = item.opportunity.exit_at
        if current is None:
            draw_ranges[draw_index] = (start, end)
        else:
            draw_ranges[draw_index] = (
                min(current[0], start),
                max(current[1], end),
            )

    ordered = [draw_ranges[index] for index in sorted(draw_ranges)]
    for left, right in zip(ordered, ordered[1:], strict=False):
        assert left[1] < right[0]


def test_phase20e_capital_state_monte_carlo_replays_reservations_not_independent_pnl() -> None:
    contract = Phase19CapitalNumeraireContract(
        contract_id="PHASE20E_SYNTHETIC_CONTRACT"
    )
    summary = run_phase20e_capital_state_monte_carlo(
        contract=contract,
        initial_capital_ncu=Decimal("10"),
        trades=_population(),
        simulations=25,
        draws_per_path=6,
        components_per_block=1,
        base_seed=20020,
    )

    assert summary.simulation_count == 25
    assert summary.source_block_count == 3
    assert summary.components_per_block == 1
    assert summary.draws_per_path == 6
    assert len(summary.path_results) == 25
    assert summary.capacity_breach_paths == 0
    assert summary.max_rejected_opportunities == 0
    assert summary.p95_max_drawdown_ncu >= 0
    assert summary.independent_trade_shuffle is False
    assert summary.market_probability_claimed is False
    assert summary.policy_certified is False

    repeated = run_phase20e_capital_state_monte_carlo(
        contract=contract,
        initial_capital_ncu=Decimal("10"),
        trades=_population(),
        simulations=25,
        draws_per_path=6,
        components_per_block=1,
        base_seed=20020,
    )
    assert repeated == summary
